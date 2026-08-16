from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urljoin

from playwright.sync_api import Locator, Page

from cip.adapters.sources.public_web.browser_action_authorization import (
    authorize_browser_action_transition,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionKind,
    BrowserActionPlan,
    BrowserActionStep,
    BrowserHttpMethod,
)
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


class BrowserActionExecutionError(RuntimeError):
    """A typed public browser action plan could not complete safely."""


class BrowserActionPolicyDeniedError(BrowserActionExecutionError):
    """A typed browser action or resulting request violated policy."""


class BrowserActionNeedsVerificationError(BrowserActionExecutionError):
    """An ambiguous non-idempotent step requires human/provider verification."""


@dataclass(slots=True)
class BrowserActionRuntimeState:
    requests_seen: int = 0
    requests_blocked: int = 0
    denial: str | None = None
    submission_guard: tuple[str, BrowserHttpMethod] | None = None
    completed_step_ids: list[str] = field(default_factory=list)


StepHandler = Callable[[Page, BrowserActionStep, int, BrowserActionRuntimeState], None]


def preflight_step(
    page: Page,
    target: PublicWebTarget,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    step: BrowserActionStep,
    *,
    now: datetime,
) -> None:
    if step.kind is BrowserActionKind.NAVIGATE:
        _preflight_navigation(target, entry, plan, step, now=now)
        return
    locator = exact_locator(page, step.selector)
    if step.kind is BrowserActionKind.CLICK:
        _preflight_click(target, entry, plan, page, locator, now=now)
    elif step.kind is BrowserActionKind.FILL:
        _deny_sensitive_fill(locator)
    elif step.kind in {BrowserActionKind.CHECK, BrowserActionKind.UNCHECK}:
        _validate_check_target(locator, allow_radio=step.kind is BrowserActionKind.CHECK)
    elif step.kind is BrowserActionKind.SUBMIT_FORM:
        _inspect_form(target, entry, plan, page, locator, step, now=now)


def execute_step(
    page: Page,
    step: BrowserActionStep,
    *,
    timeout: int,
    state: BrowserActionRuntimeState,
) -> None:
    handler = _STEP_HANDLERS.get(step.kind)
    if handler is None:
        raise BrowserActionExecutionError("unsupported_browser_action_kind")
    handler(page, step, timeout, state)


def exact_locator(page: Page, selector: str | None) -> Locator:
    if selector is None:
        raise BrowserActionExecutionError("browser_action_selector_missing")
    locator = page.locator(selector)
    if locator.count() != 1:
        raise BrowserActionPolicyDeniedError("browser_action_selector_not_unique")
    return locator


def submit_guard_allows(
    canonical_url: str,
    method: BrowserHttpMethod,
    guard: tuple[str, BrowserHttpMethod] | None,
) -> bool:
    if guard is None:
        return True
    expected_url, expected_method = guard
    actual = CanonicalUrl(canonical_url)
    expected = CanonicalUrl(expected_url)
    same_destination = actual.origin == expected.origin and actual.path == expected.path
    return method is expected_method and same_destination


def _preflight_navigation(
    target: PublicWebTarget,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    step: BrowserActionStep,
    *,
    now: datetime,
) -> None:
    if step.target_url is None:
        raise BrowserActionExecutionError("browser_action_navigation_target_missing")
    authorize_browser_action_transition(
        target,
        entry,
        plan,
        step.target_url,
        BrowserHttpMethod.GET,
        now=now,
    )


def _preflight_click(
    target: PublicWebTarget,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    page: Page,
    locator: Locator,
    *,
    now: datetime,
) -> None:
    input_type = (locator.get_attribute("type") or "").casefold()
    if input_type in {"submit", "image"}:
        raise BrowserActionPolicyDeniedError("submit_requires_typed_submit_form")
    is_button = locator.locator("xpath=self::button").count() == 1
    if is_button and input_type != "button":
        raise BrowserActionPolicyDeniedError("submit_button_requires_typed_submit_form")
    href = locator.get_attribute("href")
    if href is not None:
        authorize_browser_action_transition(
            target,
            entry,
            plan,
            urljoin(page.url, href),
            BrowserHttpMethod.GET,
            now=now,
        )


def _inspect_form(
    target: PublicWebTarget,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    page: Page,
    form: Locator,
    step: BrowserActionStep,
    *,
    now: datetime,
) -> None:
    if form.locator("xpath=self::form").count() != 1:
        raise BrowserActionPolicyDeniedError("submit_selector_must_resolve_to_form")
    action = urljoin(page.url, form.get_attribute("action") or page.url)
    raw_method = (form.get_attribute("method") or "GET").strip().upper()
    try:
        method = BrowserHttpMethod(raw_method)
    except ValueError as exc:
        raise BrowserActionPolicyDeniedError("form_method_not_supported") from exc
    expected_url = CanonicalUrl(step.expected_form_action_url or "").value
    expected_method = step.expected_form_method
    if CanonicalUrl(action).value != expected_url or method is not expected_method:
        raise BrowserActionPolicyDeniedError("form_metadata_does_not_match_plan")
    _inspect_form_fields(form)
    _submit_control(form)
    authorize_browser_action_transition(target, entry, plan, action, method, now=now)


def _inspect_form_fields(form: Locator) -> None:
    for form_field in form.locator("input, textarea, select").all():
        field_type = (form_field.get_attribute("type") or "").casefold()
        if field_type == "password":
            raise BrowserActionPolicyDeniedError("password_field_denied")
        if field_type == "file":
            raise BrowserActionPolicyDeniedError("file_input_denied")


def _submit_control(form: Locator) -> Locator:
    controls = form.locator(
        'button[type="submit"], button:not([type]), input[type="submit"]'
    )
    if controls.count() < 1:
        raise BrowserActionPolicyDeniedError("form_submit_control_missing")
    return controls.first


def _deny_sensitive_fill(locator: Locator) -> None:
    field_type = (locator.get_attribute("type") or "").casefold()
    if field_type in {"password", "file", "hidden"}:
        raise BrowserActionPolicyDeniedError("sensitive_fill_target_denied")


def _validate_check_target(locator: Locator, *, allow_radio: bool) -> None:
    field_type = (locator.get_attribute("type") or "").casefold()
    allowed = {"checkbox", "radio"} if allow_radio else {"checkbox"}
    if field_type not in allowed:
        raise BrowserActionPolicyDeniedError("check_target_type_denied")


def _navigate(
    page: Page,
    step: BrowserActionStep,
    timeout: int,
    state: BrowserActionRuntimeState,
) -> None:
    del state
    if step.target_url is None:
        raise BrowserActionExecutionError("browser_action_navigation_target_missing")
    page.goto(step.target_url, wait_until="domcontentloaded", timeout=timeout)


def _wait_navigation(
    page: Page,
    step: BrowserActionStep,
    timeout: int,
    state: BrowserActionRuntimeState,
) -> None:
    del step, state
    page.wait_for_load_state("domcontentloaded", timeout=timeout)


def _click(
    page: Page,
    step: BrowserActionStep,
    timeout: int,
    state: BrowserActionRuntimeState,
) -> None:
    del state
    exact_locator(page, step.selector).click(timeout=timeout)


def _fill(
    page: Page,
    step: BrowserActionStep,
    timeout: int,
    state: BrowserActionRuntimeState,
) -> None:
    del state
    if step.value is None:
        raise BrowserActionExecutionError("browser_action_value_missing")
    exact_locator(page, step.selector).fill(step.value, timeout=timeout)


def _select(
    page: Page,
    step: BrowserActionStep,
    timeout: int,
    state: BrowserActionRuntimeState,
) -> None:
    del state
    if step.value is None:
        raise BrowserActionExecutionError("browser_action_value_missing")
    exact_locator(page, step.selector).select_option(step.value, timeout=timeout)


def _check(
    page: Page,
    step: BrowserActionStep,
    timeout: int,
    state: BrowserActionRuntimeState,
) -> None:
    del state
    exact_locator(page, step.selector).check(timeout=timeout)


def _uncheck(
    page: Page,
    step: BrowserActionStep,
    timeout: int,
    state: BrowserActionRuntimeState,
) -> None:
    del state
    exact_locator(page, step.selector).uncheck(timeout=timeout)


def _wait_dom(
    page: Page,
    step: BrowserActionStep,
    timeout: int,
    state: BrowserActionRuntimeState,
) -> None:
    del state
    exact_locator(page, step.selector).wait_for(state="attached", timeout=timeout)


def _submit_form(
    page: Page,
    step: BrowserActionStep,
    timeout: int,
    state: BrowserActionRuntimeState,
) -> None:
    if step.expected_form_action_url is None or step.expected_form_method is None:
        raise BrowserActionExecutionError("browser_action_form_metadata_missing")
    state.submission_guard = (
        CanonicalUrl(step.expected_form_action_url).value,
        step.expected_form_method,
    )
    try:
        _submit_control(exact_locator(page, step.selector)).click(timeout=timeout)
    finally:
        state.submission_guard = None


_STEP_HANDLERS: dict[BrowserActionKind, StepHandler] = {
    BrowserActionKind.NAVIGATE: _navigate,
    BrowserActionKind.CLICK: _click,
    BrowserActionKind.FILL: _fill,
    BrowserActionKind.SELECT: _select,
    BrowserActionKind.CHECK: _check,
    BrowserActionKind.UNCHECK: _uncheck,
    BrowserActionKind.SUBMIT_FORM: _submit_form,
    BrowserActionKind.WAIT_FOR_NAVIGATION: _wait_navigation,
    BrowserActionKind.WAIT_FOR_DOM_CONDITION: _wait_dom,
}

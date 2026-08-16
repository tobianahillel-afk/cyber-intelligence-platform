from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urljoin

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, Page, Request, Route, sync_playwright

from cip.adapters.sources.public_web.browser_action_authorization import (
    BrowserActionAuthorizationError,
    authorize_browser_action_transition,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionCheckpoint,
    BrowserActionKind,
    BrowserActionPlan,
    BrowserActionStep,
    BrowserHttpMethod,
    BrowserStepState,
)
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl
from cip.modules.public_footprint.infrastructure.browser_action_persistence import (
    recover_interrupted_checkpoint,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc

CheckpointWriter = Callable[[BrowserActionCheckpoint], None]
_BLOCKED_RESOURCE_TYPES = frozenset({"font", "image", "media"})


class BrowserActionExecutionError(RuntimeError):
    """A typed public browser action plan could not complete safely."""


class BrowserActionPolicyDeniedError(BrowserActionExecutionError):
    """A typed browser action or resulting request violated policy."""


class BrowserActionNeedsVerificationError(BrowserActionExecutionError):
    """An ambiguous non-idempotent step requires human/provider verification."""


@dataclass(frozen=True, slots=True)
class BrowserActionLimits:
    max_requests: int = 64
    default_step_timeout_ms: int = 15_000

    def __post_init__(self) -> None:
        if not 1 <= self.max_requests <= 1_000:
            raise ValueError("max_requests must be between 1 and 1000")
        if not 100 <= self.default_step_timeout_ms <= 120_000:
            raise ValueError("default_step_timeout_ms must be between 100 and 120000")


@dataclass(frozen=True, slots=True)
class BrowserActionExecutionResult:
    final_url: str
    html: bytes
    checkpoint: BrowserActionCheckpoint
    completed_step_ids: tuple[str, ...]
    requests_seen: int
    requests_blocked: int


@dataclass(slots=True)
class _ActionRuntimeState:
    requests_seen: int = 0
    requests_blocked: int = 0
    denial: str | None = None
    submission_guard: tuple[str, BrowserHttpMethod] | None = None
    completed_step_ids: list[str] = field(default_factory=list)


def execute_public_browser_action_plan(
    target: PublicWebTarget,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    checkpoint: BrowserActionCheckpoint,
    *,
    collected_at: datetime,
    checkpoint_writer: CheckpointWriter,
    limits: BrowserActionLimits | None = None,
) -> BrowserActionExecutionResult:
    now = require_aware_utc(collected_at, field_name="collected_at")
    effective_limits = limits or BrowserActionLimits()
    current = recover_interrupted_checkpoint(plan, checkpoint)
    if current != checkpoint:
        checkpoint_writer(current)
    _raise_if_verification_required(current)
    state = _ActionRuntimeState()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, chromium_sandbox=True)
            context = browser.new_context(
                accept_downloads=False,
                bypass_csp=False,
                ignore_https_errors=False,
                java_script_enabled=True,
                service_workers="block",
            )
            try:
                page = context.new_page()
                page.route(
                    "**/*",
                    lambda route: _handle_route(
                        route,
                        target=target,
                        entry=entry,
                        plan=plan,
                        now=now,
                        limits=effective_limits,
                        state=state,
                    ),
                )
                current = _execute_remaining_steps(
                    page,
                    target,
                    entry,
                    plan,
                    current,
                    now=now,
                    checkpoint_writer=checkpoint_writer,
                    limits=effective_limits,
                    state=state,
                )
                if state.denial is not None:
                    raise BrowserActionPolicyDeniedError(state.denial)
                return BrowserActionExecutionResult(
                    final_url=CanonicalUrl(page.url).value,
                    html=page.content().encode("utf-8"),
                    checkpoint=current,
                    completed_step_ids=tuple(state.completed_step_ids),
                    requests_seen=state.requests_seen,
                    requests_blocked=state.requests_blocked,
                )
            finally:
                context.close()
                browser.close()
    except BrowserActionExecutionError:
        raise
    except (BrowserActionAuthorizationError, PlaywrightError, ValueError) as exc:
        if state.denial is not None:
            raise BrowserActionPolicyDeniedError(state.denial) from exc
        raise BrowserActionExecutionError("browser_action_execution_failed") from exc


def _execute_remaining_steps(
    page: Page,
    target: PublicWebTarget,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    checkpoint: BrowserActionCheckpoint,
    *,
    now: datetime,
    checkpoint_writer: CheckpointWriter,
    limits: BrowserActionLimits,
    state: _ActionRuntimeState,
) -> BrowserActionCheckpoint:
    current = checkpoint
    for index, step in enumerate(plan.steps):
        step_state = current.step_states[index]
        if step_state is BrowserStepState.COMPLETED:
            continue
        if step_state is BrowserStepState.NEEDS_VERIFICATION:
            raise BrowserActionNeedsVerificationError("browser_action_needs_verification")
        if step_state is not BrowserStepState.PENDING:
            raise BrowserActionExecutionError("browser_action_checkpoint_not_resumable")
        _preflight_step(page, target, entry, plan, step, now=now)
        current = _replace_step_state(current, index, BrowserStepState.EXECUTING)
        checkpoint_writer(current)
        _execute_step(page, step, limits=limits, state=state)
        if state.denial is not None:
            raise BrowserActionPolicyDeniedError(state.denial)
        current = _replace_step_state(current, index, BrowserStepState.COMPLETED)
        checkpoint_writer(current)
        state.completed_step_ids.append(step.step_id)
    return current


def _preflight_step(
    page: Page,
    target: PublicWebTarget,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    step: BrowserActionStep,
    *,
    now: datetime,
) -> None:
    if step.kind is BrowserActionKind.NAVIGATE:
        assert step.target_url is not None
        authorize_browser_action_transition(
            target,
            entry,
            plan,
            step.target_url,
            BrowserHttpMethod.GET,
            now=now,
        )
        return
    locator = _exact_locator(page, step.selector)
    if step.kind is BrowserActionKind.CLICK:
        _preflight_click(target, entry, plan, page, locator, now=now)
    elif step.kind is BrowserActionKind.FILL:
        _deny_sensitive_fill(locator)
    elif step.kind in {BrowserActionKind.CHECK, BrowserActionKind.UNCHECK}:
        _validate_check_target(locator, allow_radio=step.kind is BrowserActionKind.CHECK)
    elif step.kind is BrowserActionKind.SUBMIT_FORM:
        _inspect_form(target, entry, plan, page, locator, step, now=now)


def _execute_step(
    page: Page,
    step: BrowserActionStep,
    *,
    limits: BrowserActionLimits,
    state: _ActionRuntimeState,
) -> None:
    timeout = step.timeout_ms or limits.default_step_timeout_ms
    if step.kind is BrowserActionKind.NAVIGATE:
        assert step.target_url is not None
        page.goto(step.target_url, wait_until="domcontentloaded", timeout=timeout)
        return
    if step.kind is BrowserActionKind.WAIT_FOR_NAVIGATION:
        page.wait_for_load_state("domcontentloaded", timeout=timeout)
        return
    locator = _exact_locator(page, step.selector)
    if step.kind is BrowserActionKind.CLICK:
        locator.click(timeout=timeout)
    elif step.kind is BrowserActionKind.FILL:
        assert step.value is not None
        locator.fill(step.value, timeout=timeout)
    elif step.kind is BrowserActionKind.SELECT:
        assert step.value is not None
        locator.select_option(step.value, timeout=timeout)
    elif step.kind is BrowserActionKind.CHECK:
        locator.check(timeout=timeout)
    elif step.kind is BrowserActionKind.UNCHECK:
        locator.uncheck(timeout=timeout)
    elif step.kind is BrowserActionKind.WAIT_FOR_DOM_CONDITION:
        locator.wait_for(state="attached", timeout=timeout)
    elif step.kind is BrowserActionKind.SUBMIT_FORM:
        assert step.expected_form_action_url is not None
        assert step.expected_form_method is not None
        state.submission_guard = (
            CanonicalUrl(step.expected_form_action_url).value,
            step.expected_form_method,
        )
        try:
            _submit_control(locator).click(timeout=timeout)
        finally:
            state.submission_guard = None
    else:
        raise BrowserActionExecutionError("unsupported_browser_action_kind")


def _handle_route(
    route: Route,
    *,
    target: PublicWebTarget,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    now: datetime,
    limits: BrowserActionLimits,
    state: _ActionRuntimeState,
) -> None:
    request = route.request
    state.requests_seen += 1
    if state.requests_seen > limits.max_requests:
        _deny_route(route, state, "browser_action_request_budget_exceeded")
        return
    if request.resource_type in _BLOCKED_RESOURCE_TYPES:
        state.requests_blocked += 1
        route.abort()
        return
    method = _request_method(request)
    try:
        canonical = authorize_browser_action_transition(
            target,
            entry,
            plan,
            request.url,
            method,
            now=now,
        )
        _enforce_submission_guard(request, canonical, method, state.submission_guard)
    except (BrowserActionAuthorizationError, ValueError) as exc:
        _deny_route(route, state, str(exc))
        return
    route.continue_()


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
    if locator.locator("xpath=self::button").count() == 1 and input_type != "button":
        raise BrowserActionPolicyDeniedError("submit_button_requires_typed_submit_form")
    href = locator.get_attribute("href")
    if href:
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


def _exact_locator(page: Page, selector: str | None) -> Locator:
    if selector is None:
        raise BrowserActionExecutionError("browser_action_selector_missing")
    locator = page.locator(selector)
    if locator.count() != 1:
        raise BrowserActionPolicyDeniedError("browser_action_selector_not_unique")
    return locator


def _request_method(request: Request) -> BrowserHttpMethod:
    try:
        return BrowserHttpMethod(request.method.upper())
    except ValueError as exc:
        raise BrowserActionAuthorizationError("browser_action_method_not_supported") from exc


def _enforce_submission_guard(
    request: Request,
    canonical_url: str,
    method: BrowserHttpMethod,
    guard: tuple[str, BrowserHttpMethod] | None,
) -> None:
    if guard is None or not request.is_navigation_request():
        return
    expected_url, expected_method = guard
    actual = CanonicalUrl(canonical_url)
    expected = CanonicalUrl(expected_url)
    wrong_destination = actual.origin != expected.origin or actual.path != expected.path
    if method is not expected_method or wrong_destination:
        raise BrowserActionAuthorizationError("browser_action_submission_guard_denied")


def _replace_step_state(
    checkpoint: BrowserActionCheckpoint,
    index: int,
    state: BrowserStepState,
) -> BrowserActionCheckpoint:
    states = list(checkpoint.step_states)
    states[index] = state
    return BrowserActionCheckpoint(
        plan_id=checkpoint.plan_id,
        plan_version=checkpoint.plan_version,
        step_states=tuple(states),
    )


def _raise_if_verification_required(checkpoint: BrowserActionCheckpoint) -> None:
    if BrowserStepState.NEEDS_VERIFICATION in checkpoint.step_states:
        raise BrowserActionNeedsVerificationError("browser_action_needs_verification")


def _deny_route(route: Route, state: _ActionRuntimeState, reason: str) -> None:
    state.requests_blocked += 1
    state.denial = reason
    route.abort()

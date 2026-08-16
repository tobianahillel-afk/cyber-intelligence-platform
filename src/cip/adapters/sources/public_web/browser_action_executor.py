from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, Request, Route, sync_playwright

from cip.adapters.sources.public_web.browser_action_authorization import (
    BrowserActionAuthorizationError,
    authorize_browser_action_transition,
)
from cip.adapters.sources.public_web.browser_action_steps import (
    BrowserActionExecutionError,
    BrowserActionNeedsVerificationError,
    BrowserActionPolicyDeniedError,
    BrowserActionRuntimeState,
    execute_step,
    preflight_step,
    submit_guard_allows,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionCheckpoint,
    BrowserActionPlan,
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
    state = BrowserActionRuntimeState()
    try:
        return _run_browser(
            target,
            entry,
            plan,
            current,
            now=now,
            checkpoint_writer=checkpoint_writer,
            limits=effective_limits,
            state=state,
        )
    except BrowserActionExecutionError:
        raise
    except (BrowserActionAuthorizationError, PlaywrightError, ValueError) as exc:
        if state.denial is not None:
            raise BrowserActionPolicyDeniedError(state.denial) from exc
        raise BrowserActionExecutionError("browser_action_execution_failed") from exc


def _run_browser(
    target: PublicWebTarget,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    checkpoint: BrowserActionCheckpoint,
    *,
    now: datetime,
    checkpoint_writer: CheckpointWriter,
    limits: BrowserActionLimits,
    state: BrowserActionRuntimeState,
) -> BrowserActionExecutionResult:
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
            _install_request_guard(
                page,
                target,
                entry,
                plan,
                now=now,
                limits=limits,
                state=state,
            )
            current = _execute_remaining_steps(
                page,
                target,
                entry,
                plan,
                checkpoint,
                now=now,
                checkpoint_writer=checkpoint_writer,
                limits=limits,
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


def _install_request_guard(
    page: Page,
    target: PublicWebTarget,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    *,
    now: datetime,
    limits: BrowserActionLimits,
    state: BrowserActionRuntimeState,
) -> None:
    page.route(
        "**/*",
        lambda route: _handle_route(
            route,
            target=target,
            entry=entry,
            plan=plan,
            now=now,
            limits=limits,
            state=state,
        ),
    )


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
    state: BrowserActionRuntimeState,
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
        preflight_step(page, target, entry, plan, step, now=now)
        current = _replace_step_state(current, index, BrowserStepState.EXECUTING)
        checkpoint_writer(current)
        timeout = step.timeout_ms or limits.default_step_timeout_ms
        execute_step(page, step, timeout=timeout, state=state)
        if state.denial is not None:
            raise BrowserActionPolicyDeniedError(state.denial)
        current = _replace_step_state(current, index, BrowserStepState.COMPLETED)
        checkpoint_writer(current)
        state.completed_step_ids.append(step.step_id)
    return current


def _handle_route(
    route: Route,
    *,
    target: PublicWebTarget,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    now: datetime,
    limits: BrowserActionLimits,
    state: BrowserActionRuntimeState,
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
    if not request.is_navigation_request():
        return
    if not submit_guard_allows(canonical_url, method, guard):
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


def _deny_route(
    route: Route,
    state: BrowserActionRuntimeState,
    reason: str,
) -> None:
    state.requests_blocked += 1
    state.denial = reason
    route.abort()

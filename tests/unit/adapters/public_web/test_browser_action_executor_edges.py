from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest

from cip.adapters.sources.public_web import browser_action_executor as executor
from cip.adapters.sources.public_web.browser_action_authorization import (
    BrowserActionAuthorizationError,
)
from cip.adapters.sources.public_web.browser_action_steps import (
    BrowserActionExecutionError,
    BrowserActionNeedsVerificationError,
    BrowserActionPolicyDeniedError,
    BrowserActionRuntimeState,
)
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionCheckpoint,
    BrowserActionKind,
    BrowserActionPlan,
    BrowserActionStep,
    BrowserHttpMethod,
    BrowserStepState,
    BrowserTransitionRule,
)

NOW = datetime(2026, 8, 16, 17, 0, tzinfo=UTC)


def _plan() -> BrowserActionPlan:
    return BrowserActionPlan(
        plan_id=uuid4(),
        version=1,
        source_id="source",
        provider_id="provider",
        target_id="target",
        purpose="corporate-public-footprint",
        steps=(
            BrowserActionStep(
                step_id="navigate",
                kind=BrowserActionKind.NAVIGATE,
                target_url="https://example.com/public/form",
            ),
        ),
        allowed_transitions=(
            BrowserTransitionRule(
                host="example.com",
                path_prefix="/public",
                methods=frozenset({BrowserHttpMethod.GET}),
            ),
        ),
        max_actions=1,
        max_total_value_chars=0,
    )


def _checkpoint(plan: BrowserActionPlan, state: BrowserStepState) -> BrowserActionCheckpoint:
    return BrowserActionCheckpoint(
        plan_id=plan.plan_id,
        plan_version=plan.version,
        step_states=(state,),
    )


def _run_context(
    *,
    checkpoint_writer: Callable[[BrowserActionCheckpoint], None] | None = None,
    limits: executor.BrowserActionLimits | None = None,
    state: BrowserActionRuntimeState | None = None,
) -> executor._BrowserRunContext:
    return executor._BrowserRunContext(
        now=NOW,
        checkpoint_writer=checkpoint_writer or (lambda _: None),
        limits=limits or executor.BrowserActionLimits(),
        action_state=state or BrowserActionRuntimeState(),
        artifact_context=None,
        artifact_state=executor.BrowserArtifactRuntimeState(),
    )


class _Request:
    def __init__(
        self,
        *,
        method: str = "GET",
        resource_type: str = "document",
        url: str = "https://example.com/public/form",
        navigation: bool = True,
    ) -> None:
        self.method = method
        self.resource_type = resource_type
        self.url = url
        self.navigation = navigation

    def is_navigation_request(self) -> bool:
        return self.navigation


class _Route:
    def __init__(self, request: _Request) -> None:
        self.request = request
        self.aborted = False
        self.continued = False

    def abort(self) -> None:
        self.aborted = True

    def continue_(self) -> None:
        self.continued = True


def test_limits_reject_out_of_range_values() -> None:
    for value in (0, 1_001):
        with pytest.raises(ValueError, match="max_requests"):
            executor.BrowserActionLimits(max_requests=value)
    for value in (99, 120_001):
        with pytest.raises(ValueError, match="default_step_timeout_ms"):
            executor.BrowserActionLimits(default_step_timeout_ms=value)


def test_top_level_persists_recovery_and_wraps_untyped_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _plan()
    interrupted = _checkpoint(plan, BrowserStepState.EXECUTING)
    recovered = _checkpoint(plan, BrowserStepState.PENDING)
    writes: list[BrowserActionCheckpoint] = []
    result = executor.BrowserActionExecutionResult(
        final_url="https://example.com/public/form",
        html=b"ok",
        checkpoint=_checkpoint(plan, BrowserStepState.COMPLETED),
        completed_step_ids=("navigate",),
        requests_seen=1,
        requests_blocked=0,
    )
    monkeypatch.setattr(executor, "recover_interrupted_checkpoint", lambda *_: recovered)
    monkeypatch.setattr(executor, "_run_browser", lambda *args, **kwargs: result)

    actual = executor.execute_public_browser_action_plan(
        cast(Any, object()),
        cast(Any, object()),
        plan,
        interrupted,
        collected_at=NOW,
        checkpoint_writer=writes.append,
    )
    assert actual is result
    assert writes == [recovered]

    def _authorization_failure(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise BrowserActionAuthorizationError("denied")

    monkeypatch.setattr(executor, "_run_browser", _authorization_failure)
    with pytest.raises(BrowserActionExecutionError, match="execution_failed"):
        executor.execute_public_browser_action_plan(
            cast(Any, object()),
            cast(Any, object()),
            plan,
            recovered,
            collected_at=NOW,
            checkpoint_writer=lambda _: None,
        )


def test_top_level_preserves_typed_error_and_policy_denial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _plan()
    checkpoint = _checkpoint(plan, BrowserStepState.PENDING)

    def _typed_failure(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise BrowserActionNeedsVerificationError("typed")

    monkeypatch.setattr(executor, "_run_browser", _typed_failure)
    with pytest.raises(BrowserActionNeedsVerificationError, match="typed"):
        executor.execute_public_browser_action_plan(
            cast(Any, object()),
            cast(Any, object()),
            plan,
            checkpoint,
            collected_at=NOW,
            checkpoint_writer=lambda _: None,
        )

    state = SimpleNamespace(denial="policy-denied")
    monkeypatch.setattr(executor, "BrowserActionRuntimeState", lambda: state)

    def _value_failure(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise ValueError("boom")

    monkeypatch.setattr(executor, "_run_browser", _value_failure)
    with pytest.raises(BrowserActionPolicyDeniedError, match="policy-denied"):
        executor.execute_public_browser_action_plan(
            cast(Any, object()),
            cast(Any, object()),
            plan,
            checkpoint,
            collected_at=NOW,
            checkpoint_writer=lambda _: None,
        )


def test_verification_and_non_resumable_states_fail_before_execution() -> None:
    plan = _plan()
    verification = _checkpoint(plan, BrowserStepState.NEEDS_VERIFICATION)
    with pytest.raises(BrowserActionNeedsVerificationError, match="needs_verification"):
        executor._raise_if_verification_required(verification)

    with pytest.raises(BrowserActionNeedsVerificationError, match="needs_verification"):
        executor._execute_remaining_steps(
            cast(Any, object()),
            cast(Any, object()),
            cast(Any, object()),
            plan,
            verification,
            run=_run_context(),
        )

    executing = _checkpoint(plan, BrowserStepState.EXECUTING)
    with pytest.raises(BrowserActionExecutionError, match="checkpoint_not_resumable"):
        executor._execute_remaining_steps(
            cast(Any, object()),
            cast(Any, object()),
            cast(Any, object()),
            plan,
            executing,
            run=_run_context(),
        )


def test_remaining_steps_skip_completed_and_persist_transitions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _plan()
    completed = _checkpoint(plan, BrowserStepState.COMPLETED)
    assert (
        executor._execute_remaining_steps(
            cast(Any, object()),
            cast(Any, object()),
            cast(Any, object()),
            plan,
            completed,
            run=_run_context(
                checkpoint_writer=lambda _: pytest.fail(
                    "completed step must not be rewritten"
                )
            ),
        )
        == completed
    )

    monkeypatch.setattr(executor, "preflight_step", lambda *args, **kwargs: None)
    monkeypatch.setattr(executor, "execute_step", lambda *args, **kwargs: None)
    pending = _checkpoint(plan, BrowserStepState.PENDING)
    writes: list[BrowserActionCheckpoint] = []
    state = BrowserActionRuntimeState()
    result = executor._execute_remaining_steps(
        cast(Any, object()),
        cast(Any, object()),
        cast(Any, object()),
        plan,
        pending,
        run=_run_context(
            checkpoint_writer=writes.append,
            limits=executor.BrowserActionLimits(default_step_timeout_ms=321),
            state=state,
        ),
    )
    assert [item.step_states[0] for item in writes] == [
        BrowserStepState.EXECUTING,
        BrowserStepState.COMPLETED,
    ]
    assert result.step_states == (BrowserStepState.COMPLETED,)
    assert state.completed_step_ids == ["navigate"]


def test_remaining_step_denial_stops_before_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _plan()
    monkeypatch.setattr(executor, "preflight_step", lambda *args, **kwargs: None)

    def _deny(*args: object, **kwargs: object) -> None:
        state = cast(BrowserActionRuntimeState, kwargs["state"])
        state.denial = "network-denied"

    monkeypatch.setattr(executor, "execute_step", _deny)
    writes: list[BrowserActionCheckpoint] = []
    state = BrowserActionRuntimeState()
    with pytest.raises(BrowserActionPolicyDeniedError, match="network-denied"):
        executor._execute_remaining_steps(
            cast(Any, object()),
            cast(Any, object()),
            cast(Any, object()),
            plan,
            _checkpoint(plan, BrowserStepState.PENDING),
            run=_run_context(checkpoint_writer=writes.append, state=state),
        )
    assert writes[-1].step_states == (BrowserStepState.EXECUTING,)


def test_request_method_submission_guard_and_route_denials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert executor._request_method(cast(Any, _Request(method="get"))) is BrowserHttpMethod.GET
    with pytest.raises(BrowserActionAuthorizationError, match="method_not_supported"):
        executor._request_method(cast(Any, _Request(method="PATCH")))

    executor._enforce_submission_guard(
        cast(Any, _Request(navigation=False)),
        "https://example.com/public/form",
        BrowserHttpMethod.GET,
        ("https://example.com/other", BrowserHttpMethod.POST),
    )
    with pytest.raises(BrowserActionAuthorizationError, match="submission_guard_denied"):
        executor._enforce_submission_guard(
            cast(Any, _Request(navigation=True)),
            "https://example.com/public/form",
            BrowserHttpMethod.GET,
            ("https://example.com/other", BrowserHttpMethod.POST),
        )

    plan = _plan()
    target = cast(Any, object())
    entry = cast(Any, object())

    state = BrowserActionRuntimeState(requests_seen=1)
    budget_route = _Route(_Request())
    executor._handle_route(
        cast(Any, budget_route),
        target=target,
        entry=entry,
        plan=plan,
        run=_run_context(
            limits=executor.BrowserActionLimits(max_requests=1),
            state=state,
        ),
    )
    assert budget_route.aborted
    assert state.denial == "browser_action_request_budget_exceeded"

    blocked_state = BrowserActionRuntimeState()
    blocked_route = _Route(_Request(resource_type="image"))
    executor._handle_route(
        cast(Any, blocked_route),
        target=target,
        entry=entry,
        plan=plan,
        run=_run_context(state=blocked_state),
    )
    assert blocked_route.aborted
    assert blocked_state.denial is None
    assert blocked_state.requests_blocked == 1

    unsupported_state = BrowserActionRuntimeState()
    unsupported_route = _Route(_Request(method="PATCH"))
    executor._handle_route(
        cast(Any, unsupported_route),
        target=target,
        entry=entry,
        plan=plan,
        run=_run_context(state=unsupported_state),
    )
    assert unsupported_route.aborted
    assert "method_not_supported" in (unsupported_state.denial or "")

    monkeypatch.setattr(
        executor,
        "authorize_browser_action_transition",
        lambda *args, **kwargs: "https://example.com/public/form",
    )
    allowed_state = BrowserActionRuntimeState()
    allowed_route = _Route(_Request(navigation=False))
    executor._handle_route(
        cast(Any, allowed_route),
        target=target,
        entry=entry,
        plan=plan,
        run=_run_context(state=allowed_state),
    )
    assert allowed_route.continued

    guarded_state = BrowserActionRuntimeState(
        submission_guard=("https://example.com/public/other", BrowserHttpMethod.POST)
    )
    guarded_route = _Route(_Request(navigation=True))
    executor._handle_route(
        cast(Any, guarded_route),
        target=target,
        entry=entry,
        plan=plan,
        run=_run_context(state=guarded_state),
    )
    assert guarded_route.aborted
    assert "submission_guard_denied" in (guarded_state.denial or "")

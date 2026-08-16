from __future__ import annotations

from uuid import uuid4

import pytest

from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionCheckpoint,
    BrowserActionKind,
    BrowserActionPlan,
    BrowserActionStep,
    BrowserHttpMethod,
    BrowserStepState,
    BrowserTransitionRule,
)


def _transition() -> BrowserTransitionRule:
    return BrowserTransitionRule(
        host="example.com",
        path_prefix="/public",
        methods=frozenset({BrowserHttpMethod.GET}),
    )


def _navigate() -> BrowserActionStep:
    return BrowserActionStep(
        step_id="navigate",
        kind=BrowserActionKind.NAVIGATE,
        target_url="https://example.com/public/form",
    )


def _plan(**overrides: object) -> BrowserActionPlan:
    values: dict[str, object] = {
        "plan_id": uuid4(),
        "version": 1,
        "source_id": "source",
        "provider_id": "provider",
        "target_id": "target",
        "purpose": "purpose",
        "steps": (_navigate(),),
        "allowed_transitions": (_transition(),),
        "max_actions": 1,
        "max_total_value_chars": 0,
    }
    values.update(overrides)
    return BrowserActionPlan(**values)  # type: ignore[arg-type]


def test_step_rejects_invalid_identity_and_timeout_bounds() -> None:
    with pytest.raises(ValueError, match="step_id is invalid"):
        BrowserActionStep(
            step_id="",
            kind=BrowserActionKind.CLICK,
            selector="button#go",
        )

    with pytest.raises(ValueError, match="timeout_ms must be between"):
        BrowserActionStep(
            step_id="wait",
            kind=BrowserActionKind.WAIT_FOR_NAVIGATION,
            timeout_ms=0,
        )


def test_plan_rejects_invalid_version_shape_and_budget_bounds() -> None:
    with pytest.raises(ValueError, match="version must be positive"):
        _plan(version=0)
    with pytest.raises(ValueError, match="between 1 and 32 steps"):
        _plan(steps=())
    with pytest.raises(ValueError, match="between 1 and 32 transitions"):
        _plan(allowed_transitions=())
    with pytest.raises(ValueError, match="max_actions must be between"):
        _plan(max_actions=0)
    with pytest.raises(ValueError, match="max_total_value_chars is outside"):
        _plan(max_total_value_chars=-1)


def test_checkpoint_rejects_invalid_version_empty_state_and_non_pending_tail() -> None:
    with pytest.raises(ValueError, match="version must be positive"):
        BrowserActionCheckpoint(
            plan_id=uuid4(),
            plan_version=0,
            step_states=(BrowserStepState.PENDING,),
        )
    with pytest.raises(ValueError, match="step_states are invalid"):
        BrowserActionCheckpoint(
            plan_id=uuid4(),
            plan_version=1,
            step_states=(),
        )
    with pytest.raises(ValueError, match="must end with pending steps"):
        BrowserActionCheckpoint(
            plan_id=uuid4(),
            plan_version=1,
            step_states=(
                BrowserStepState.EXECUTING,
                BrowserStepState.NEEDS_VERIFICATION,
            ),
        )


def test_selector_navigation_and_submit_required_fields_fail_closed() -> None:
    with pytest.raises(ValueError, match="click requires a selector"):
        BrowserActionStep(step_id="click", kind=BrowserActionKind.CLICK)
    with pytest.raises(ValueError, match="navigate requires target_url"):
        BrowserActionStep(step_id="navigate", kind=BrowserActionKind.NAVIGATE)
    with pytest.raises(ValueError, match="submit_form requires expected form action and method"):
        BrowserActionStep(
            step_id="submit",
            kind=BrowserActionKind.SUBMIT_FORM,
            selector="form#search",
        )


def test_bounded_text_rejects_nul_and_oversized_transition_fields() -> None:
    with pytest.raises(ValueError, match="selector is invalid"):
        BrowserActionStep(
            step_id="click",
            kind=BrowserActionKind.CLICK,
            selector="button\x00unsafe",
        )
    with pytest.raises(ValueError, match="host is invalid"):
        BrowserTransitionRule(
            host="x" * 201,
            path_prefix="/public",
            methods=frozenset({BrowserHttpMethod.GET}),
        )
    with pytest.raises(ValueError, match="path_prefix is invalid"):
        BrowserTransitionRule(
            host="example.com",
            path_prefix="/" + "x" * 1001,
            methods=frozenset({BrowserHttpMethod.GET}),
        )

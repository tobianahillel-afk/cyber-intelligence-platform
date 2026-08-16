from __future__ import annotations

from uuid import uuid4

import pytest

from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionCheckpoint,
    BrowserActionKind,
    BrowserActionPlan,
    BrowserActionStep,
    BrowserHttpMethod,
    BrowserStepReplayPolicy,
    BrowserStepState,
    BrowserTransitionRule,
    BrowserValueClassification,
)


def _transition() -> BrowserTransitionRule:
    return BrowserTransitionRule(
        host="Example.COM",
        path_prefix="/public",
        methods=frozenset({BrowserHttpMethod.GET, BrowserHttpMethod.POST}),
    )


def _navigate() -> BrowserActionStep:
    return BrowserActionStep(
        step_id="open-form",
        kind=BrowserActionKind.NAVIGATE,
        target_url="https://example.com/public/form",
    )


def _fill() -> BrowserActionStep:
    return BrowserActionStep(
        step_id="fill-query",
        kind=BrowserActionKind.FILL,
        selector='input[name="query"]',
        value="public company name",
        value_classification=BrowserValueClassification.PUBLIC_NON_SECRET,
    )


def _post_submit() -> BrowserActionStep:
    return BrowserActionStep(
        step_id="submit-form",
        kind=BrowserActionKind.SUBMIT_FORM,
        selector="form#public-search",
        expected_form_action_url="https://example.com/public/search",
        expected_form_method=BrowserHttpMethod.POST,
        replay_policy=BrowserStepReplayPolicy.VERIFY_BEFORE_REPLAY,
    )


def test_plan_accepts_reviewed_public_action_shapes() -> None:
    steps = (
        _navigate(),
        BrowserActionStep(
            step_id="click-advanced",
            kind=BrowserActionKind.CLICK,
            selector="button#advanced",
        ),
        _fill(),
        BrowserActionStep(
            step_id="select-category",
            kind=BrowserActionKind.SELECT,
            selector="select#category",
            value="public",
            value_classification=BrowserValueClassification.PUBLIC_NON_SECRET,
        ),
        BrowserActionStep(
            step_id="check-confirm",
            kind=BrowserActionKind.CHECK,
            selector="input#confirm",
        ),
        _post_submit(),
        BrowserActionStep(
            step_id="wait-navigation",
            kind=BrowserActionKind.WAIT_FOR_NAVIGATION,
            timeout_ms=5_000,
        ),
        BrowserActionStep(
            step_id="wait-result",
            kind=BrowserActionKind.WAIT_FOR_DOM_CONDITION,
            selector="main#results",
            timeout_ms=5_000,
        ),
    )

    plan = BrowserActionPlan(
        plan_id=uuid4(),
        version=1,
        source_id="public-browser-source",
        provider_id="public-browser-provider",
        target_id="example-public-form",
        purpose="approved-public-form-research",
        steps=steps,
        allowed_transitions=(_transition(),),
        max_actions=8,
        max_total_value_chars=100,
    )

    assert plan.steps == steps
    assert plan.allowed_transitions[0].host == "example.com"


def test_fill_and_select_require_explicit_public_non_secret_values() -> None:
    with pytest.raises(ValueError, match="explicitly public non-secret"):
        BrowserActionStep(
            step_id="unsafe-fill",
            kind=BrowserActionKind.FILL,
            selector="input#name",
            value="text",
        )

    with pytest.raises(ValueError, match="explicitly public non-secret"):
        BrowserActionStep(
            step_id="unsafe-select",
            kind=BrowserActionKind.SELECT,
            selector="select#type",
            value="option",
        )


def test_post_submit_cannot_be_blindly_replay_safe() -> None:
    with pytest.raises(ValueError, match="cannot be blindly replayable"):
        BrowserActionStep(
            step_id="unsafe-post",
            kind=BrowserActionKind.SUBMIT_FORM,
            selector="form#search",
            expected_form_action_url="https://example.com/public/search",
            expected_form_method=BrowserHttpMethod.POST,
            replay_policy=BrowserStepReplayPolicy.SAFE,
        )


def test_step_shape_rejects_generic_cross_action_fields() -> None:
    with pytest.raises(ValueError, match="navigate does not allow selector"):
        BrowserActionStep(
            step_id="bad-navigation",
            kind=BrowserActionKind.NAVIGATE,
            selector="a#next",
            target_url="https://example.com/public/next",
        )

    with pytest.raises(ValueError, match="click does not allow value"):
        BrowserActionStep(
            step_id="bad-click",
            kind=BrowserActionKind.CLICK,
            selector="button#go",
            value="caller-command",
        )


def test_plan_enforces_action_value_and_identity_budgets() -> None:
    with pytest.raises(ValueError, match="exceeds max_actions"):
        BrowserActionPlan(
            plan_id=uuid4(),
            version=1,
            source_id="source",
            provider_id="provider",
            target_id="target",
            purpose="purpose",
            steps=(_navigate(), _fill()),
            allowed_transitions=(_transition(),),
            max_actions=1,
            max_total_value_chars=100,
        )

    with pytest.raises(ValueError, match="exceeds max_total_value_chars"):
        BrowserActionPlan(
            plan_id=uuid4(),
            version=1,
            source_id="source",
            provider_id="provider",
            target_id="target",
            purpose="purpose",
            steps=(_fill(),),
            allowed_transitions=(_transition(),),
            max_actions=1,
            max_total_value_chars=1,
        )

    duplicate = BrowserActionStep(
        step_id="same",
        kind=BrowserActionKind.CLICK,
        selector="button#one",
    )
    with pytest.raises(ValueError, match="step ids must be unique"):
        BrowserActionPlan(
            plan_id=uuid4(),
            version=1,
            source_id="source",
            provider_id="provider",
            target_id="target",
            purpose="purpose",
            steps=(
                duplicate,
                BrowserActionStep(
                    step_id="same",
                    kind=BrowserActionKind.CHECK,
                    selector="input#two",
                ),
            ),
            allowed_transitions=(_transition(),),
            max_actions=2,
            max_total_value_chars=0,
        )


def test_transition_rules_are_bounded_and_host_only() -> None:
    with pytest.raises(ValueError, match="host is invalid"):
        BrowserTransitionRule(
            host="https://example.com/path",
            path_prefix="/public",
            methods=frozenset({BrowserHttpMethod.GET}),
        )
    with pytest.raises(ValueError, match="path_prefix is invalid"):
        BrowserTransitionRule(
            host="example.com",
            path_prefix="public",
            methods=frozenset({BrowserHttpMethod.GET}),
        )
    with pytest.raises(ValueError, match="methods cannot be empty"):
        BrowserTransitionRule(
            host="example.com",
            path_prefix="/public",
            methods=frozenset(),
        )


def test_checkpoint_requires_completed_prefix_and_pending_tail() -> None:
    checkpoint = BrowserActionCheckpoint(
        plan_id=uuid4(),
        plan_version=1,
        step_states=(
            BrowserStepState.COMPLETED,
            BrowserStepState.NEEDS_VERIFICATION,
            BrowserStepState.PENDING,
        ),
    )
    assert checkpoint.step_states[1] is BrowserStepState.NEEDS_VERIFICATION

    with pytest.raises(ValueError, match="must end with pending steps"):
        BrowserActionCheckpoint(
            plan_id=uuid4(),
            plan_version=1,
            step_states=(
                BrowserStepState.PENDING,
                BrowserStepState.COMPLETED,
            ),
        )

    with pytest.raises(ValueError, match="must end with pending steps"):
        BrowserActionCheckpoint(
            plan_id=uuid4(),
            plan_version=1,
            step_states=(
                BrowserStepState.NEEDS_VERIFICATION,
                BrowserStepState.EXECUTING,
            ),
        )


def test_checkpoint_allows_only_one_current_step() -> None:
    with pytest.raises(ValueError, match="must end with pending steps"):
        BrowserActionCheckpoint(
            plan_id=uuid4(),
            plan_version=1,
            step_states=(
                BrowserStepState.EXECUTING,
                BrowserStepState.NEEDS_VERIFICATION,
            ),
        )

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionCheckpoint,
    BrowserActionKind,
    BrowserActionPlan,
    BrowserActionStep,
    BrowserHttpMethod,
    BrowserStepReplayPolicy,
    BrowserStepState,
    BrowserTransitionRule,
)
from cip.modules.public_footprint.infrastructure.browser_action_models import (
    BrowserActionCheckpointRecord,
    BrowserActionPlanRecord,
)
from cip.modules.public_footprint.infrastructure.browser_action_persistence import (
    load_browser_action_checkpoint,
    load_browser_action_plan,
    persist_browser_action_plan,
    recover_interrupted_checkpoint,
    save_browser_action_checkpoint,
)

NOW = datetime(2026, 8, 16, 15, 0, tzinfo=UTC)


def _plan(*, post: bool = False) -> BrowserActionPlan:
    submit = BrowserActionStep(
        step_id="submit",
        kind=BrowserActionKind.SUBMIT_FORM,
        selector="form#search",
        expected_form_action_url="https://example.com/public/search",
        expected_form_method=(BrowserHttpMethod.POST if post else BrowserHttpMethod.GET),
        replay_policy=(
            BrowserStepReplayPolicy.VERIFY_BEFORE_REPLAY
            if post
            else BrowserStepReplayPolicy.SAFE
        ),
    )
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
            submit,
        ),
        allowed_transitions=(
            BrowserTransitionRule(
                host="example.com",
                path_prefix="/public",
                methods=frozenset({BrowserHttpMethod.GET, BrowserHttpMethod.POST}),
            ),
        ),
        max_actions=2,
        max_total_value_chars=0,
    )


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    BrowserActionPlanRecord.__table__.create(engine)
    BrowserActionCheckpointRecord.__table__.create(engine)
    return Session(engine)


def test_plan_round_trip_is_immutable_and_creates_pending_checkpoint() -> None:
    plan = _plan()
    with _session() as session:
        checkpoint = persist_browser_action_plan(session, plan, now=NOW)
        session.commit()

        assert checkpoint.step_states == (
            BrowserStepState.PENDING,
            BrowserStepState.PENDING,
        )
        assert load_browser_action_plan(session, plan.plan_id, 1) == plan
        assert load_browser_action_checkpoint(session, plan.plan_id, 1) == checkpoint
        assert persist_browser_action_plan(session, plan, now=NOW) == checkpoint


def test_plan_identity_collision_fails_closed() -> None:
    plan = _plan()
    with _session() as session:
        persist_browser_action_plan(session, plan, now=NOW)
        session.commit()
        conflicting = BrowserActionPlan(
            plan_id=plan.plan_id,
            version=plan.version,
            source_id=plan.source_id,
            provider_id=plan.provider_id,
            target_id=plan.target_id,
            purpose="different-purpose",
            steps=plan.steps,
            allowed_transitions=plan.allowed_transitions,
            max_actions=plan.max_actions,
            max_total_value_chars=plan.max_total_value_chars,
        )
        with pytest.raises(ValueError, match="identity collision"):
            persist_browser_action_plan(session, conflicting, now=NOW)


def test_checkpoint_save_requires_known_matching_plan() -> None:
    plan = _plan()
    with _session() as session:
        persist_browser_action_plan(session, plan, now=NOW)
        completed = BrowserActionCheckpoint(
            plan_id=plan.plan_id,
            plan_version=1,
            step_states=(BrowserStepState.COMPLETED, BrowserStepState.PENDING),
        )
        save_browser_action_checkpoint(session, completed, now=NOW)
        assert load_browser_action_checkpoint(session, plan.plan_id, 1) == completed

        unknown = BrowserActionCheckpoint(
            plan_id=uuid4(),
            plan_version=1,
            step_states=(BrowserStepState.PENDING,),
        )
        with pytest.raises(ValueError, match="unknown plan"):
            save_browser_action_checkpoint(session, unknown, now=NOW)


def test_recovery_retries_safe_get_but_blocks_ambiguous_post() -> None:
    get_plan = _plan(post=False)
    safe_interrupted = BrowserActionCheckpoint(
        plan_id=get_plan.plan_id,
        plan_version=1,
        step_states=(BrowserStepState.COMPLETED, BrowserStepState.EXECUTING),
    )
    assert recover_interrupted_checkpoint(get_plan, safe_interrupted).step_states == (
        BrowserStepState.COMPLETED,
        BrowserStepState.PENDING,
    )

    post_plan = _plan(post=True)
    unsafe_interrupted = BrowserActionCheckpoint(
        plan_id=post_plan.plan_id,
        plan_version=1,
        step_states=(BrowserStepState.COMPLETED, BrowserStepState.EXECUTING),
    )
    assert recover_interrupted_checkpoint(post_plan, unsafe_interrupted).step_states == (
        BrowserStepState.COMPLETED,
        BrowserStepState.NEEDS_VERIFICATION,
    )


def test_recovery_rejects_checkpoint_from_another_plan() -> None:
    plan = _plan()
    checkpoint = BrowserActionCheckpoint(
        plan_id=uuid4(),
        plan_version=1,
        step_states=(BrowserStepState.PENDING, BrowserStepState.PENDING),
    )
    with pytest.raises(ValueError, match="does not belong"):
        recover_interrupted_checkpoint(plan, checkpoint)

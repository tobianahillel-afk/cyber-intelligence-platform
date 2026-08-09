from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cip.modules.research_orchestration.domain import (
    ResearchBudget,
    ResearchPlan,
    ResearchPlanState,
    ResearchRiskLevel,
    ResearchRuntimeState,
    ResearchStep,
    ResearchStepMode,
    ResearchStepState,
    ResearchUsage,
)
from cip.modules.research_orchestration.infrastructure.attempt_persistence import (
    begin_research_attempt,
    complete_research_attempt,
    mark_external_action_started,
)
from cip.modules.research_orchestration.infrastructure.decision_persistence import (
    evaluate_and_persist_step_decision,
)
from cip.modules.research_orchestration.infrastructure.models import (
    ResearchPlanRecord,
    ResearchPlanRevisionRecord,
    ResearchResultRecord,
    ResearchStepAttemptRecord,
    ResearchStepDecisionRecord,
    ResearchStepRecord,
)
from cip.modules.research_orchestration.infrastructure.plan_persistence import (
    persist_research_plan,
)
from cip.modules.research_orchestration.infrastructure.result_persistence import (
    ResearchResultCapture,
    record_research_result,
)
from cip.modules.research_orchestration.infrastructure.step_persistence import (
    persist_research_step,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.shared.persistence.base import Base
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 9, 15, 0, tzinfo=UTC)
PLAN_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")


def test_plan_replay_is_idempotent_and_revision_history_is_immutable() -> None:
    session = _session()
    plan = _plan()

    first = _persist_plan(session, plan, NOW, "initial plan")
    _persist_plan(session, plan, NOW + timedelta(minutes=1), "retry")
    changed = replace(plan, question="Updated bounded research question")
    current = _persist_plan(
        session,
        changed,
        NOW + timedelta(minutes=2),
        "refine research question",
    )

    assert current.id == first.id
    assert current.question == "Updated bounded research question"
    assert _count(session, ResearchPlanRecord) == 1
    assert _count(session, ResearchPlanRevisionRecord) == 2
    revisions = tuple(
        session.scalars(
            select(ResearchPlanRevisionRecord).order_by(
                ResearchPlanRevisionRecord.created_at
            )
        )
    )
    assert revisions[0].change_reason == "initial plan"
    assert revisions[1].change_reason == "refine research question"


def test_step_definition_replay_is_idempotent_but_mutation_is_rejected() -> None:
    session = _session_with_plan()
    step = _step()

    first = persist_research_step(session, PLAN_ID, step, now=NOW)
    replay = persist_research_step(
        session,
        PLAN_ID,
        step,
        now=NOW + timedelta(minutes=1),
    )

    assert replay.id == first.id
    assert _count(session, ResearchStepRecord) == 1
    with pytest.raises(ValueError, match="cannot mutate"):
        persist_research_step(
            session,
            PLAN_ID,
            replace(step, target_url="https://search.example.test/other"),
            now=NOW + timedelta(minutes=2),
        )


def test_step_decision_is_replay_safe_and_updates_current_state() -> None:
    session = _session_with_plan_and_step()
    plan = _plan()
    step = _step()
    usage = ResearchUsage()
    runtime = _runtime()

    decision = evaluate_and_persist_step_decision(
        session,
        plan,
        step,
        usage,
        runtime,
        now=NOW + timedelta(minutes=1),
    )
    evaluate_and_persist_step_decision(
        session,
        plan,
        step,
        usage,
        runtime,
        now=NOW + timedelta(minutes=1),
    )

    record = session.scalar(select(ResearchStepRecord))
    assert decision.allowed is True
    assert record is not None
    assert record.state == ResearchStepState.READY.value
    assert _count(session, ResearchStepDecisionRecord) == 1


def test_attempt_idempotency_prevents_duplicate_external_action() -> None:
    session = _session_with_ready_step()

    first = begin_research_attempt(
        session,
        PLAN_ID,
        "step-1",
        actor="researcher@example.test",
        idempotency_key="request-123",
        now=NOW + timedelta(minutes=2),
    )
    replay = begin_research_attempt(
        session,
        PLAN_ID,
        "step-1",
        actor="researcher@example.test",
        idempotency_key="request-123",
        now=NOW + timedelta(minutes=3),
    )
    started = mark_external_action_started(
        session,
        first.id,
        reference="collection-job:abc",
        now=NOW + timedelta(minutes=4),
    )
    same = mark_external_action_started(
        session,
        first.id,
        reference="collection-job:abc",
        now=NOW + timedelta(minutes=5),
    )

    assert replay.id == first.id
    assert started.external_action_started is True
    assert same.external_action_reference == "collection-job:abc"
    assert _count(session, ResearchStepAttemptRecord) == 1
    with pytest.raises(ValueError, match="different reference"):
        mark_external_action_started(
            session,
            first.id,
            reference="collection-job:different",
            now=NOW + timedelta(minutes=6),
        )


def test_manual_link_attempt_never_masquerades_as_automated_action() -> None:
    session = _session_with_plan()
    manual = replace(_step(), mode=ResearchStepMode.MANUAL_LINK)
    persist_research_step(session, PLAN_ID, manual, now=NOW)
    evaluate_and_persist_step_decision(
        session,
        _plan(),
        manual,
        ResearchUsage(),
        replace(_runtime(), source_authorized=False, source_executable=False),
        now=NOW + timedelta(minutes=1),
    )
    attempt = begin_research_attempt(
        session,
        PLAN_ID,
        "step-1",
        actor="researcher@example.test",
        idempotency_key="manual-1",
        now=NOW + timedelta(minutes=2),
    )

    assert attempt.state == ResearchStepState.MANUAL_ACTION_REQUIRED.value
    assert attempt.external_action_started is False
    with pytest.raises(ValueError, match="automated-adapter"):
        mark_external_action_started(
            session,
            attempt.id,
            reference="should-not-exist",
            now=NOW + timedelta(minutes=3),
        )


def test_result_replay_converges_on_evidence_and_provenance_references() -> None:
    session = _session_with_ready_step()
    attempt = begin_research_attempt(
        session,
        PLAN_ID,
        "step-1",
        actor="researcher@example.test",
        idempotency_key="request-result",
        now=NOW + timedelta(minutes=2),
    )
    complete_research_attempt(
        session,
        attempt.id,
        now=NOW + timedelta(minutes=3),
    )

    first = _result(session, attempt.id)
    replay = _result(session, attempt.id)

    assert first.id == replay.id
    assert first.evidence_reference == "evidence:public-resource:42"
    assert first.provenance_reference == "source-record:abc123"
    assert _count(session, ResearchResultRecord) == 1


def _session() -> Session:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return create_session_factory(engine)()


def _session_with_plan() -> Session:
    session = _session()
    _persist_plan(session, _plan(), NOW, "initial plan")
    return session


def _session_with_plan_and_step() -> Session:
    session = _session_with_plan()
    persist_research_step(session, PLAN_ID, _step(), now=NOW)
    return session


def _session_with_ready_step() -> Session:
    session = _session_with_plan_and_step()
    evaluate_and_persist_step_decision(
        session,
        _plan(),
        _step(),
        ResearchUsage(),
        _runtime(),
        now=NOW + timedelta(minutes=1),
    )
    return session


def _persist_plan(
    session: Session,
    plan: ResearchPlan,
    now: datetime,
    reason: str,
) -> ResearchPlanRecord:
    return persist_research_plan(
        session,
        plan,
        actor="research-lead@example.test",
        change_reason=reason,
        now=now,
    )


def _result(session: Session, attempt_id: UUID) -> ResearchResultRecord:
    capture = ResearchResultCapture(
        attempt_id=attempt_id,
        result_type="evidence_reference",
        evidence_reference="evidence:public-resource:42",
        provenance_reference="source-record:abc123",
        source_id="search-catalog",
        summary="Bounded analyst summary",
        recorded_by="researcher@example.test",
    )
    return record_research_result(
        session,
        PLAN_ID,
        "step-1",
        capture,
        now=NOW + timedelta(minutes=4),
    )


def _count(session: Session, model: type[object]) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def _plan() -> ResearchPlan:
    return ResearchPlan(
        plan_id=PLAN_ID,
        question="What public evidence supports Acme's cloud security priorities?",
        purpose="organization-research",
        data_category=DataCategory.ORGANIZATION_METADATA,
        state=ResearchPlanState.APPROVED,
        budget=ResearchBudget(10, 3, 20.0, 5.0),
        allowed_source_ids=frozenset({"search-catalog"}),
        allowed_tool_ids=frozenset({"approved-search"}),
        approved_step_keys=frozenset({"step-1"}),
        allowed_hosts=frozenset({"search.example.test"}),
        allowed_path_prefixes=("/results",),
        max_risk_level=ResearchRiskLevel.MEDIUM,
        expires_at=NOW + timedelta(hours=4),
    )


def _step() -> ResearchStep:
    return ResearchStep(
        step_key="step-1",
        sequence=1,
        source_id="search-catalog",
        tool_id="approved-search",
        mode=ResearchStepMode.AUTOMATED_ADAPTER,
        purpose="organization-research",
        data_category=DataCategory.ORGANIZATION_METADATA,
        estimated_cost=1.0,
        risk_level=ResearchRiskLevel.LOW,
        target_url="https://search.example.test/results?q=acme",
        query_text="site:acme.example security cloud",
    )


def _runtime() -> ResearchRuntimeState:
    return ResearchRuntimeState(
        source_authorized=True,
        source_executable=True,
        adapter_capability_present=True,
        manual_link_allowed=True,
        ingestion_path_approved=True,
        quota_remaining=100,
    )

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

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
    ResearchUsage,
)
from cip.modules.research_orchestration.infrastructure.attempt_persistence import (
    begin_research_attempt,
    mark_external_action_started,
)
from cip.modules.research_orchestration.infrastructure.decision_persistence import (
    evaluate_and_persist_step_decision,
)
from cip.modules.research_orchestration.infrastructure.models import (
    ResearchStepAttemptRecord,
)
from cip.modules.research_orchestration.infrastructure.plan_persistence import (
    persist_research_plan,
)
from cip.modules.research_orchestration.infrastructure.step_persistence import (
    persist_research_step,
)
from cip.modules.research_orchestration.infrastructure.usage import resolve_research_usage
from cip.modules.source_governance.domain.models import DataCategory
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 9, 18, 0, tzinfo=UTC)
PLAN_ID = UUID("33333333-3333-4333-8333-333333333333")
IDEMPOTENCY_KEY = "interrupted-request-42"


def test_interrupted_running_attempt_replays_without_duplicate_external_action() -> None:
    session = _ready_session()
    first = begin_research_attempt(
        session,
        PLAN_ID,
        "automated-1",
        actor="analyst@example.test",
        idempotency_key=IDEMPOTENCY_KEY,
        now=NOW + timedelta(minutes=1),
    )
    started = mark_external_action_started(
        session,
        first.id,
        reference="collection-job:interrupted-42",
        now=NOW + timedelta(minutes=2),
    )

    replay = begin_research_attempt(
        session,
        PLAN_ID,
        "automated-1",
        actor="analyst@example.test",
        idempotency_key=IDEMPOTENCY_KEY,
        now=NOW + timedelta(hours=1),
    )
    replayed_action = mark_external_action_started(
        session,
        replay.id,
        reference="collection-job:interrupted-42",
        now=NOW + timedelta(hours=1, minutes=1),
    )
    usage = resolve_research_usage(session, PLAN_ID)

    assert replay.id == first.id == started.id == replayed_action.id
    assert replay.external_action_started is True
    assert replay.external_action_reference == "collection-job:interrupted-42"
    assert _attempt_count(session) == 1
    assert usage.completed_steps == 0
    assert usage.automated_steps == 1
    assert usage.cost_used == 2.5


def _ready_session() -> Session:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    session = create_session_factory(engine)()
    plan = _plan()
    step = _step()
    persist_research_plan(
        session,
        plan,
        actor="research-lead@example.test",
        change_reason="approved recovery test plan",
        now=NOW,
    )
    persist_research_step(session, PLAN_ID, step, now=NOW)
    evaluate_and_persist_step_decision(
        session,
        plan,
        step,
        ResearchUsage(),
        _runtime(),
        now=NOW,
    )
    return session


def _attempt_count(session: Session) -> int:
    return int(
        session.scalar(select(func.count()).select_from(ResearchStepAttemptRecord)) or 0
    )


def _plan() -> ResearchPlan:
    return ResearchPlan(
        plan_id=PLAN_ID,
        question="Can interrupted governed research resume without duplicate execution?",
        purpose="organization-research",
        data_category=DataCategory.ORGANIZATION_METADATA,
        state=ResearchPlanState.APPROVED,
        budget=ResearchBudget(
            max_steps=3,
            max_automated_steps=1,
            max_total_cost=5.0,
            max_step_cost=3.0,
        ),
        allowed_source_ids=frozenset({"approved-source"}),
        allowed_tool_ids=frozenset({"approved-adapter"}),
        approved_step_keys=frozenset({"automated-1"}),
        allowed_hosts=frozenset({"research.example.test"}),
        allowed_path_prefixes=("/results",),
        max_risk_level=ResearchRiskLevel.LOW,
        expires_at=NOW + timedelta(days=1),
    )


def _step() -> ResearchStep:
    return ResearchStep(
        step_key="automated-1",
        sequence=1,
        source_id="approved-source",
        tool_id="approved-adapter",
        mode=ResearchStepMode.AUTOMATED_ADAPTER,
        purpose="organization-research",
        data_category=DataCategory.ORGANIZATION_METADATA,
        estimated_cost=2.5,
        risk_level=ResearchRiskLevel.LOW,
        target_url="https://research.example.test/results?q=acme",
        query_text="acme",
    )


def _runtime() -> ResearchRuntimeState:
    return ResearchRuntimeState(
        source_authorized=True,
        source_executable=True,
        adapter_capability_present=True,
        manual_link_allowed=False,
        ingestion_path_approved=False,
        quota_remaining=100,
    )

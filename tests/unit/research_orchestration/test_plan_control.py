from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cip.modules.research_orchestration.domain import (
    ResearchBudget,
    ResearchDecisionType,
    ResearchPlan,
    ResearchPlanState,
    ResearchRiskLevel,
)
from cip.modules.research_orchestration.infrastructure.models import (
    ResearchPlanDecisionRecord,
    ResearchPlanRecord,
    ResearchPlanRevisionRecord,
)
from cip.modules.research_orchestration.infrastructure.plan_control import (
    apply_research_plan_decision,
)
from cip.modules.research_orchestration.infrastructure.plan_persistence import (
    persist_research_plan,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 9, 16, 45, tzinfo=UTC)
PLAN_ID = UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
ACTOR = "research-lead@example.test"


def test_approval_appends_revision_and_decision() -> None:
    session = _session_with_plan()

    decision = _decide(session, ResearchDecisionType.APPROVE, "bounded plan reviewed")
    plan = session.get(ResearchPlanRecord, PLAN_ID)

    assert plan is not None
    assert plan.state == ResearchPlanState.APPROVED.value
    assert decision.previous_state == ResearchPlanState.DRAFT.value
    assert decision.resulting_state == ResearchPlanState.APPROVED.value
    assert _count(session, ResearchPlanRevisionRecord) == 2
    assert _count(session, ResearchPlanDecisionRecord) == 1


def test_same_decision_replay_is_idempotent_after_state_change() -> None:
    session = _session_with_plan()

    first = _decide(session, ResearchDecisionType.APPROVE, "bounded plan reviewed")
    replay = _decide(
        session,
        ResearchDecisionType.APPROVE,
        "bounded plan reviewed",
        at=NOW + timedelta(minutes=1),
    )

    assert replay.id == first.id
    assert _count(session, ResearchPlanDecisionRecord) == 1
    assert _count(session, ResearchPlanRevisionRecord) == 2


def test_pause_resume_and_complete_are_audited() -> None:
    session = _session_with_plan()
    _decide(session, ResearchDecisionType.APPROVE, "approved")
    paused = _decide(session, ResearchDecisionType.PAUSE, "analyst review")
    resumed = _decide(session, ResearchDecisionType.RESUME, "review complete")
    completed = _decide(session, ResearchDecisionType.COMPLETE, "research complete")

    assert paused.resulting_state == ResearchPlanState.PAUSED.value
    assert resumed.resulting_state == ResearchPlanState.APPROVED.value
    assert completed.resulting_state == ResearchPlanState.COMPLETED.value
    assert _count(session, ResearchPlanDecisionRecord) == 4
    assert _count(session, ResearchPlanRevisionRecord) == 5


def test_terminal_plan_rejects_new_transitions() -> None:
    session = _session_with_plan()
    _decide(session, ResearchDecisionType.CANCEL, "question withdrawn")

    with pytest.raises(ValueError, match="cannot approve from cancelled"):
        _decide(session, ResearchDecisionType.APPROVE, "late approval")


def test_reject_is_only_valid_before_approval() -> None:
    draft_session = _session_with_plan()
    rejected = _decide(draft_session, ResearchDecisionType.REJECT, "scope denied")
    assert rejected.resulting_state == ResearchPlanState.CANCELLED.value

    approved_session = _session_with_plan()
    _decide(approved_session, ResearchDecisionType.APPROVE, "approved")
    with pytest.raises(ValueError, match="cannot reject from approved"):
        _decide(approved_session, ResearchDecisionType.REJECT, "too late")


def _session() -> Session:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return create_session_factory(engine)()


def _session_with_plan() -> Session:
    session = _session()
    persist_research_plan(
        session,
        _plan(),
        actor=ACTOR,
        change_reason="initial draft",
        now=NOW,
    )
    return session


def _decide(
    session: Session,
    decision_type: ResearchDecisionType,
    reason: str,
    *,
    at: datetime = NOW,
) -> ResearchPlanDecisionRecord:
    return apply_research_plan_decision(
        session,
        PLAN_ID,
        decision_type,
        actor=ACTOR,
        reason=reason,
        now=at,
    )


def _count(session: Session, model: type[object]) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def _plan() -> ResearchPlan:
    return ResearchPlan(
        plan_id=PLAN_ID,
        question="What bounded public evidence should the analyst review?",
        purpose="organization-research",
        data_category=DataCategory.ORGANIZATION_METADATA,
        state=ResearchPlanState.DRAFT,
        budget=ResearchBudget(5, 2, 10.0, 3.0),
        allowed_source_ids=frozenset({"search-catalog"}),
        allowed_tool_ids=frozenset({"manual-search"}),
        approved_step_keys=frozenset({"step-1"}),
        allowed_hosts=frozenset({"search.example.test"}),
        allowed_path_prefixes=("/results",),
        max_risk_level=ResearchRiskLevel.MEDIUM,
        expires_at=NOW + timedelta(hours=8),
    )

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from cip.modules.research_orchestration.domain import ResearchStepMode, ResearchStepState
from cip.modules.research_orchestration.infrastructure.models import (
    ResearchStepAttemptRecord,
    ResearchStepRecord,
)
from cip.modules.research_orchestration.infrastructure.usage import resolve_research_usage
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 9, 16, 30, tzinfo=UTC)
PLAN_ID = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
STEP_ID = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddd01")
ATTEMPT_ID = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddd02")


def test_usage_is_zero_without_persisted_steps_or_attempts() -> None:
    usage = resolve_research_usage(_session(), PLAN_ID)

    assert usage.completed_steps == 0
    assert usage.automated_steps == 0
    assert usage.cost_used == 0.0


def test_usage_counts_external_automated_step_once() -> None:
    session = _session()
    session.add(_step())
    session.add(_attempt())
    session.flush()

    usage = resolve_research_usage(session, PLAN_ID)

    assert usage.completed_steps == 1
    assert usage.automated_steps == 1
    assert usage.cost_used == 2.5


def test_running_external_automated_step_already_consumes_budget() -> None:
    session = _session()
    session.add(_step(state=ResearchStepState.RUNNING))
    session.add(_attempt(state=ResearchStepState.RUNNING, completed_at=None))
    session.flush()

    usage = resolve_research_usage(session, PLAN_ID)

    assert usage.completed_steps == 0
    assert usage.automated_steps == 1
    assert usage.cost_used == 2.5


def test_replayed_attempt_for_same_step_does_not_double_charge() -> None:
    session = _session()
    session.add(_step())
    session.add(_attempt())
    session.add(
        ResearchStepAttemptRecord(
            id=UUID("dddddddd-dddd-4ddd-8ddd-dddddddddd03"),
            plan_id=PLAN_ID,
            step_id=STEP_ID,
            attempt_key="retry-attempt",
            mode=ResearchStepMode.AUTOMATED_ADAPTER.value,
            state=ResearchStepState.COMPLETED.value,
            actor="researcher@example.test",
            external_action_started=True,
            external_action_reference="collection-job:retry",
            error_code=None,
            started_at=NOW,
            completed_at=NOW,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    session.flush()

    usage = resolve_research_usage(session, PLAN_ID)

    assert usage.automated_steps == 1
    assert usage.cost_used == 2.5


def _session() -> Session:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return create_session_factory(engine)()


def _step(
    *,
    state: ResearchStepState = ResearchStepState.COMPLETED,
) -> ResearchStepRecord:
    return ResearchStepRecord(
        id=STEP_ID,
        plan_id=PLAN_ID,
        step_key="automated-1",
        sequence=1,
        source_id="research-source",
        tool_id="research-adapter",
        mode=ResearchStepMode.AUTOMATED_ADAPTER.value,
        purpose="organization-research",
        data_category="organization_metadata",
        estimated_cost=2.5,
        risk_level="low",
        target_url="https://research.example.test/results",
        query_text="acme",
        ingestion_path_id=None,
        state=state.value,
        created_at=NOW,
        updated_at=NOW,
    )


def _attempt(
    *,
    state: ResearchStepState = ResearchStepState.COMPLETED,
    completed_at: datetime | None = NOW,
) -> ResearchStepAttemptRecord:
    return ResearchStepAttemptRecord(
        id=ATTEMPT_ID,
        plan_id=PLAN_ID,
        step_id=STEP_ID,
        attempt_key="first-attempt",
        mode=ResearchStepMode.AUTOMATED_ADAPTER.value,
        state=state.value,
        actor="researcher@example.test",
        external_action_started=True,
        external_action_reference="collection-job:first",
        error_code=None,
        started_at=NOW,
        completed_at=completed_at,
        created_at=NOW,
        updated_at=NOW,
    )

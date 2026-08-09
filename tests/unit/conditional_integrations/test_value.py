from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from cip.modules.conditional_integrations.application.value import (
    summarize_conditional_provider_value,
)
from cip.modules.source_portfolio.application.value import (
    SourceExecutionMode,
    SourceValueEvent,
    record_source_value_event,
)
from cip.modules.source_portfolio.infrastructure.models import SourcePortfolioRecord
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 9, 13, 30, tzinfo=UTC)
SOURCE_ID = "linkedin-official-api"
OTHER_SOURCE_ID = "other-provider"


def test_value_summary_requires_observed_execution_evidence() -> None:
    session = _session()
    _portfolio(session, SOURCE_ID)

    summary = summarize_conditional_provider_value(session, SOURCE_ID)

    assert summary.evidence_available is False
    assert summary.source.executions == 0
    assert summary.portfolio_without_source.executions == 0


def test_value_summary_keeps_source_and_ablation_baseline_separate() -> None:
    session = _session()
    _portfolio(session, SOURCE_ID)
    _portfolio(session, OTHER_SOURCE_ID)
    _event(
        session,
        source_id=SOURCE_ID,
        observations=12,
        commercial=3,
        identity=4,
        cost=2.5,
    )
    _event(
        session,
        source_id=OTHER_SOURCE_ID,
        observations=20,
        commercial=5,
        identity=1,
        cost=1.0,
    )

    summary = summarize_conditional_provider_value(session, SOURCE_ID)

    assert summary.evidence_available is True
    assert summary.source.executions == 1
    assert summary.source.observations_written == 12
    assert summary.source.commercial_projections == 3
    assert summary.source.identity_projections == 4
    assert summary.source.request_cost == 2.5
    assert summary.portfolio_without_source.executions == 1
    assert summary.portfolio_without_source.observations_written == 20
    assert summary.portfolio_without_source.commercial_projections == 5
    assert summary.portfolio_without_source.request_cost == 1.0


def _session() -> Session:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return create_session_factory(engine)()


def _portfolio(session: Session, source_id: str) -> None:
    session.add(
        SourcePortfolioRecord(
            source_id=source_id,
            display_name=source_id,
            canonical_url=f"https://{source_id}.example.test",
            category="conditional_test",
            status="candidate",
            freshness_max_age_seconds=86_400,
            commercial_use_cases=["test"],
            authorization_expires_at=None,
            review_due_at=None,
            candidate_origin="lot22-test",
            monthly_cost_limit=100.0,
            extra_metadata={},
            created_at=NOW,
            updated_at=NOW,
        )
    )
    session.flush()


def _event(
    session: Session,
    *,
    source_id: str,
    observations: int,
    commercial: int,
    identity: int,
    cost: float,
) -> None:
    recorded = record_source_value_event(
        session,
        SourceValueEvent(
            source_id=source_id,
            execution_id=uuid4(),
            execution_mode=SourceExecutionMode.INCREMENTAL,
            observations_written=observations,
            commercial_projections=commercial,
            identity_projections=identity,
            request_cost=cost,
            not_modified=False,
            occurred_at=NOW,
        ),
    )
    assert recorded is True

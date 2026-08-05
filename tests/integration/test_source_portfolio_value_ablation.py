from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cip.modules.source_portfolio.application.service import (
    SourceExecutionMode,
    SourceValueEvent,
    record_source_value_event,
    summarize_source_value,
    sync_source_portfolio,
)
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio
from cip.shared.persistence.metadata import get_metadata

NOW = datetime(2026, 8, 5, tzinfo=UTC)


def test_source_value_events_are_idempotent_and_support_ablation() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        sync_source_portfolio(
            session,
            load_source_portfolio(Path("policies/source_portfolio.yml")),
            now=NOW,
        )
        cisa_execution = uuid4()
        cisa_event = SourceValueEvent(
            source_id="cisa-kev",
            execution_id=cisa_execution,
            execution_mode=SourceExecutionMode.INCREMENTAL,
            observations_written=10,
            commercial_projections=3,
            identity_projections=1,
            request_cost=0.5,
            not_modified=False,
            occurred_at=NOW,
        )
        assert record_source_value_event(session, cisa_event) is True
        assert record_source_value_event(session, cisa_event) is False
        assert record_source_value_event(
            session,
            SourceValueEvent(
                source_id="ted-search",
                execution_id=uuid4(),
                execution_mode=SourceExecutionMode.INCREMENTAL,
                observations_written=4,
                commercial_projections=2,
                identity_projections=0,
                request_cost=1.0,
                not_modified=False,
                occurred_at=NOW + timedelta(minutes=1),
            ),
        )

        complete = summarize_source_value(session)
        without_cisa = summarize_source_value(
            session,
            excluded_source_id="cisa-kev",
        )
        cisa_only = summarize_source_value(session, source_id="cisa-kev")

        assert complete.executions == 2
        assert complete.observations_written == 14
        assert complete.commercial_projections == 5
        assert complete.request_cost == 1.5
        assert without_cisa.observations_written == 4
        assert without_cisa.commercial_projections == 2
        assert cisa_only.observations_written == 10
        assert cisa_only.identity_projections == 1


def test_historical_value_event_records_no_derived_projection() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        sync_source_portfolio(
            session,
            load_source_portfolio(Path("policies/source_portfolio.yml")),
            now=NOW,
        )
        record_source_value_event(
            session,
            SourceValueEvent(
                source_id="reference-synthetic",
                execution_id=uuid4(),
                execution_mode=SourceExecutionMode.HISTORICAL_BACKFILL,
                observations_written=7,
                commercial_projections=0,
                identity_projections=0,
                request_cost=0,
                not_modified=False,
                occurred_at=NOW,
            ),
        )

        summary = summarize_source_value(session, source_id="reference-synthetic")

        assert summary.observations_written == 7
        assert summary.commercial_projections == 0
        assert summary.identity_projections == 0

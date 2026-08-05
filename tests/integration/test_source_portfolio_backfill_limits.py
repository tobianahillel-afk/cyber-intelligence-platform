from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cip.modules.source_portfolio.application.backfill import MAX_BACKFILL_ATTEMPTS
from cip.modules.source_portfolio.application.service import (
    cancel_backfill,
    claim_backfill_partition,
    fail_backfill_partition,
    get_source_health,
    request_backfill,
    sync_source_portfolio,
)
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio
from cip.shared.persistence.metadata import get_metadata

NOW = datetime(2026, 8, 5, tzinfo=UTC)


def test_failed_partition_stops_after_bounded_attempts() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        sync_source_portfolio(
            session,
            load_source_portfolio(Path("policies/source_portfolio.yml")),
            now=NOW,
        )
        request_backfill(
            session,
            "reference-synthetic",
            (("2025-01-01", "2025-02-01"),),
            actor="attempt-test",
            now=NOW,
        )
        for attempt in range(MAX_BACKFILL_ATTEMPTS):
            claimed = claim_backfill_partition(
                session,
                "reference-synthetic",
                actor="worker",
                now=NOW + timedelta(seconds=attempt * 2 + 1),
            )
            assert claimed is not None
            fail_backfill_partition(
                session,
                claimed.id,
                cursor={"attempt": attempt + 1},
                error_code="provider_timeout",
                actor="worker",
                now=NOW + timedelta(seconds=attempt * 2 + 2),
            )

        assert (
            claim_backfill_partition(
                session,
                "reference-synthetic",
                actor="worker",
                now=NOW + timedelta(minutes=1),
            )
            is None
        )


def test_cancel_without_partitions_does_not_invent_backfill_state() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        sync_source_portfolio(
            session,
            load_source_portfolio(Path("policies/source_portfolio.yml")),
            now=NOW,
        )
        cancel_backfill(
            session,
            "reference-synthetic",
            actor="operator",
            now=NOW,
        )

        assert get_source_health(session, "reference-synthetic").current_backfill_state is None

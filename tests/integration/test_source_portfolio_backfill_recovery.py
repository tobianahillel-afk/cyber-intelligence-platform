from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cip.modules.source_portfolio.application.service import (
    cancel_backfill,
    claim_backfill_partition,
    fail_backfill_partition,
    get_source_health,
    request_backfill,
    sync_source_portfolio,
)
from cip.modules.source_portfolio.domain.models import BackfillState
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio
from cip.shared.persistence.metadata import get_metadata

NOW = datetime(2026, 8, 5, tzinfo=UTC)


def test_failed_partition_retries_with_cursor_preserved() -> None:
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
            actor="backfill-test",
            now=NOW,
        )
        claimed = claim_backfill_partition(
            session,
            "reference-synthetic",
            actor="worker-1",
            now=NOW + timedelta(seconds=1),
        )
        assert claimed is not None
        fail_backfill_partition(
            session,
            claimed.id,
            cursor={"page": 4},
            error_code="provider_timeout",
            actor="worker-1",
            now=NOW + timedelta(seconds=2),
        )
        failed_health = get_source_health(session, "reference-synthetic")
        assert failed_health.current_backfill_state is BackfillState.FAILED

        retried = claim_backfill_partition(
            session,
            "reference-synthetic",
            actor="worker-2",
            now=NOW + timedelta(seconds=3),
        )
        assert retried is not None
        assert retried.id == claimed.id
        assert retried.cursor == {"page": 4}
        assert retried.attempts == 2
        assert retried.state == BackfillState.RUNNING.value


def test_cancel_backfill_is_terminal_and_auditable() -> None:
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
            (("2024-01-01", "2024-02-01"),),
            actor="backfill-test",
            now=NOW,
        )
        cancel_backfill(
            session,
            "reference-synthetic",
            actor="backfill-test",
            now=NOW + timedelta(seconds=1),
        )

        health = get_source_health(session, "reference-synthetic")
        assert health.current_backfill_state is BackfillState.CANCELLED
        assert (
            claim_backfill_partition(
                session,
                "reference-synthetic",
                actor="worker-1",
                now=NOW + timedelta(seconds=2),
            )
            is None
        )

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cip.modules.collection_orchestration.application.reference_adapter import (
    ReferencePortfolioAdapter,
)
from cip.modules.source_portfolio.application.service import (
    CollectionHealthUpdate,
    SourcePortfolioStateError,
    claim_backfill_partition,
    complete_backfill_partition,
    disable_source,
    get_source_health,
    get_source_portfolio,
    pause_source,
    record_collection_failure,
    record_collection_success,
    refresh_freshness,
    request_backfill,
    resume_source,
    sync_source_portfolio,
)
from cip.modules.source_portfolio.domain.models import (
    BackfillState,
    CatalogStatus,
    FreshnessState,
    SchemaState,
)
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio
from cip.shared.persistence.metadata import get_metadata

NOW = datetime(2026, 8, 5, 0, 0, tzinfo=UTC)


def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return Session(engine)


def test_reference_adapter_and_backfill_resume_lifecycle() -> None:
    database = session()
    entries = load_source_portfolio(Path("policies/source_portfolio.yml"))
    sync_source_portfolio(database, entries, now=NOW)

    ids = request_backfill(
        database,
        "reference-synthetic",
        (("2026-01-01", "2026-02-01"), ("2026-02-01", "2026-03-01")),
        actor="integration-test",
        now=NOW,
    )
    assert len(ids) == 2

    first = claim_backfill_partition(
        database,
        "reference-synthetic",
        actor="worker-1",
        now=NOW + timedelta(seconds=1),
    )
    assert first is not None
    assert first.state == BackfillState.RUNNING.value

    adapter = ReferencePortfolioAdapter()
    batch = adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=NOW + timedelta(seconds=2),
        retention_until=NOW + timedelta(days=30),
    )
    assert batch.observations[0].source_record_key == "1"

    complete_backfill_partition(
        database,
        first.id,
        cursor=dict(batch.checkpoint_payload),
        records_written=len(batch.observations),
        actor="worker-1",
        now=NOW + timedelta(seconds=3),
    )
    health = get_source_health(database, "reference-synthetic")
    assert health.current_backfill_state is BackfillState.PENDING

    pause_source(
        database,
        "reference-synthetic",
        actor="operator",
        now=NOW + timedelta(seconds=4),
    )
    assert get_source_portfolio(database, "reference-synthetic").status is CatalogStatus.PAUSED
    assert (
        claim_backfill_partition(
            database,
            "reference-synthetic",
            actor="worker-2",
            now=NOW + timedelta(seconds=5),
        )
        is None
    )

    resume_source(
        database,
        "reference-synthetic",
        actor="operator",
        now=NOW + timedelta(seconds=6),
    )
    second = claim_backfill_partition(
        database,
        "reference-synthetic",
        actor="worker-2",
        now=NOW + timedelta(seconds=7),
    )
    assert second is not None
    complete_backfill_partition(
        database,
        second.id,
        cursor={"sequence": 2},
        records_written=1,
        actor="worker-2",
        now=NOW + timedelta(seconds=8),
    )
    health = get_source_health(database, "reference-synthetic")
    assert health.current_backfill_state is BackfillState.COMPLETED

    disable_source(
        database,
        "reference-synthetic",
        actor="operator",
        now=NOW + timedelta(seconds=9),
    )
    assert get_source_portfolio(database, "reference-synthetic").status is CatalogStatus.DISABLED
    database.close()


def test_candidate_cannot_execute_and_health_recovers() -> None:
    database = session()
    entries = load_source_portfolio(Path("policies/source_portfolio.yml"))
    sync_source_portfolio(database, entries, now=NOW)

    try:
        request_backfill(
            database,
            "osint-framework-import",
            (("a", "b"),),
            actor="integration-test",
            now=NOW,
        )
    except SourcePortfolioStateError as exc:
        assert "cannot execute" in str(exc)
    else:
        raise AssertionError("catalog candidate unexpectedly executed")

    failed = record_collection_failure(
        database,
        "cisa-kev",
        error_code="source_schema_drift",
        schema_drift=True,
        now=NOW,
    )
    assert failed.freshness_state is FreshnessState.SOURCE_UNAVAILABLE
    assert failed.schema_state is SchemaState.DRIFTED

    recovered = record_collection_success(
        database,
        "cisa-kev",
        CollectionHealthUpdate(
            source_record_at=NOW + timedelta(minutes=1),
            schema_state=SchemaState.STABLE,
            quota_remaining=5,
            cost=0,
        ),
        now=NOW + timedelta(minutes=1),
    )
    assert recovered.freshness_state is FreshnessState.FRESH
    assert recovered.consecutive_failures == 0

    stale = refresh_freshness(database, "cisa-kev", now=NOW + timedelta(hours=2))
    assert stale.freshness_state is FreshnessState.STALE_REFRESH_QUEUED
    database.close()

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import select

from cip.modules.collection_orchestration.application import runtime as runtime_module
from cip.modules.collection_orchestration.application.metrics import (
    read_source_collection_metrics,
)
from cip.modules.collection_orchestration.application.runtime import (
    CollectionRuntime,
    build_collection_runtime,
    run_scheduler_once,
)
from cip.modules.collection_orchestration.application.worker import (
    WorkerOutcome,
    WorkerStatus,
)
from cip.modules.collection_orchestration.domain.models import (
    CollectionJob,
    JobStatus,
    SourceSchedule,
)
from cip.modules.collection_orchestration.infrastructure.models import (
    CollectionCheckpointRecord,
    CollectionDeadLetterRecord,
    CollectionJobRecord,
)
from cip.modules.collection_orchestration.infrastructure.repository import enqueue_job
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.modules.source_governance.infrastructure.persistence import sync_source_registry
from cip.modules.source_governance.infrastructure.registry import load_source_registry
from cip.shared.config.settings import Settings
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import (
    create_database_engine,
    create_session_factory,
    session_scope,
)

NOW = datetime(2026, 8, 3, 18, 30, tzinfo=UTC)


def _settings(tmp_path: Path, *, schedule_path: Path | None = None) -> Settings:
    return Settings(
        _env_file=None,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'runtime.db'}",
        source_registry_path=Path("policies/sources.example.yml"),
        retention_policy_path=Path("policies/retention.yml"),
        collection_schedule_path=schedule_path or Path("policies/collection_schedules.yml"),
        scheduler_poll_seconds=0.01,
        worker_poll_seconds=0.01,
    )


def test_runtime_syncs_sources_and_schedules_idempotently(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    get_metadata().create_all(create_database_engine(settings.database_url))

    runtime = build_collection_runtime(settings)
    assert run_scheduler_once(runtime, now=NOW) == 1
    assert run_scheduler_once(runtime, now=NOW) == 0

    with session_scope(runtime.factory) as session:
        source = session.get(SourceRecord, "cisa-kev")
        job = session.scalar(select(CollectionJobRecord))
    assert source is not None
    assert source.automated_collection_allowed is True
    assert job is not None


def test_source_registry_sync_inserts_updates_and_then_stabilizes(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    engine = create_database_engine(settings.database_url)
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)
    entries = load_source_registry(settings.source_registry_path)

    with session_scope(factory) as session:
        assert sync_source_registry(session, entries) == len(entries)
    with session_scope(factory) as session:
        assert sync_source_registry(session, entries) == 0

    changed_entry = replace(
        entries[0],
        policy=entries[0].policy.model_copy(update={"name": "Updated source name"}),
    )
    with session_scope(factory) as session:
        assert sync_source_registry(session, (changed_entry, *entries[1:])) == 1
        record = session.get(SourceRecord, entries[0].policy.id)
        assert record is not None
        assert record.name == "Updated source name"


def test_runtime_rejects_enabled_schedule_without_adapter(tmp_path: Path) -> None:
    schedule = tmp_path / "schedules.yml"
    schedule.write_text(
        """version: 1
schedules:
  - source_id: cisa-kev
    adapter_id: missing-adapter
    enabled: true
    interval_seconds: 60
    lease_seconds: 30
    retry:
      max_attempts: 2
      base_delay_seconds: 5
      max_delay_seconds: 10
      circuit_failure_threshold: 2
      circuit_reset_seconds: 30
""",
        encoding="utf-8",
    )
    settings = _settings(tmp_path, schedule_path=schedule)
    get_metadata().create_all(create_database_engine(settings.database_url))

    with pytest.raises(ValueError, match="no registered adapter"):
        build_collection_runtime(settings)


def test_collection_metrics_report_freshness_lag_errors_and_volume(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    engine = create_database_engine(settings.database_url)
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)
    entries = load_source_registry(settings.source_registry_path)
    schedule = SourceSchedule("cisa-kev", "cisa-kev-feed", 900)

    with session_scope(factory) as session:
        sync_source_registry(session, entries)
        jobs = [
            CollectionJob.from_schedule(
                schedule,
                scheduled_for=NOW - timedelta(minutes=offset),
            )
            for offset in (30, 20, 10)
        ]
        for job in jobs:
            enqueue_job(session, job)
        records = list(
            session.scalars(
                select(CollectionJobRecord).order_by(CollectionJobRecord.scheduled_for)
            )
        )
        records[0].status = JobStatus.PENDING.value
        records[1].status = JobStatus.RUNNING.value
        records[2].status = JobStatus.RETRY_SCHEDULED.value
        records[2].error_code = "timeout"
        records[2].observations_written = 7
        session.add(
            CollectionCheckpointRecord(
                source_id="cisa-kev",
                adapter_id="cisa-kev-feed",
                payload={"etag": "v1"},
                version=1,
                updated_at=NOW - timedelta(minutes=1),
                last_success_at=NOW - timedelta(minutes=1),
                last_observation_at=NOW - timedelta(minutes=2),
            )
        )
        session.add(
            CollectionDeadLetterRecord(
                id=uuid4(),
                job_id=records[2].id,
                source_id="cisa-kev",
                adapter_id="cisa-kev-feed",
                failed_at=NOW - timedelta(minutes=3),
                attempt=2,
                error_code="timeout",
                error_message="failed",
                checkpoint_snapshot={"etag": "old"},
            )
        )

    with session_scope(factory) as session:
        metrics = read_source_collection_metrics(
            session,
            source_id="cisa-kev",
            adapter_id="cisa-kev-feed",
            now=NOW,
        )

    assert metrics.freshness_seconds == 60
    assert metrics.queue_lag_seconds == 1_800
    assert metrics.pending_jobs == 1
    assert metrics.running_jobs == 1
    assert metrics.retry_jobs == 1
    assert metrics.errors_24h == 1
    assert metrics.dead_letters == 1
    assert metrics.observations_written_total == 7


def test_runtime_loops_are_bounded_and_sleep_only_when_needed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_runtime = cast(CollectionRuntime, object())
    settings = Settings(_env_file=None, scheduler_poll_seconds=0.5, worker_poll_seconds=0.25)
    monkeypatch.setattr(runtime_module, "build_collection_runtime", lambda settings: fake_runtime)

    scheduler_calls: list[int] = []
    scheduler_sleeps: list[float] = []
    monkeypatch.setattr(
        runtime_module,
        "run_scheduler_once",
        lambda runtime: scheduler_calls.append(1) or 0,
    )
    runtime_module.run_scheduler_forever(
        settings,
        sleep_fn=scheduler_sleeps.append,
        max_iterations=2,
    )
    assert len(scheduler_calls) == 2
    assert scheduler_sleeps == [0.5]

    outcomes = iter(
        [
            WorkerOutcome(WorkerStatus.IDLE),
            WorkerOutcome(WorkerStatus.SUCCEEDED, job_id=uuid4()),
        ]
    )
    worker_sleeps: list[float] = []
    monkeypatch.setattr(
        runtime_module,
        "run_worker_once",
        lambda *args, **kwargs: next(outcomes),
    )
    runtime_module.run_worker_forever(
        settings,
        worker_id="worker",
        sleep_fn=worker_sleeps.append,
        max_iterations=2,
    )
    assert worker_sleeps == [0.25]

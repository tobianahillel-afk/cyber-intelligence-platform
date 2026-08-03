from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from cip.modules.collection_orchestration.application.ports import AdapterCollectionBatch
from cip.modules.collection_orchestration.application.scheduler import schedule_due_jobs
from cip.modules.collection_orchestration.domain.models import (
    CircuitState,
    JobStatus,
    RetryPolicy,
    SourceSchedule,
)
from cip.modules.collection_orchestration.infrastructure.models import (
    CollectionCheckpointRecord,
    CollectionCircuitRecord,
    CollectionDeadLetterRecord,
    CollectionJobRecord,
)
from cip.modules.collection_orchestration.infrastructure.repository import (
    LeaseLostError,
    claim_next_job,
    complete_job,
    fail_job,
    heartbeat_job,
    recover_expired_leases,
)
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.raw_observations.infrastructure.models import RawObservationRecord
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.persistence import sync_source_registry
from cip.modules.source_governance.infrastructure.registry import load_source_registry
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 3, 18, 30, tzinfo=UTC)


def _factory() -> sessionmaker[Session]:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        sync_source_registry(
            session,
            load_source_registry(Path("policies/sources.example.yml")),
        )
    return factory


def _schedule(*, threshold: int = 3, max_attempts: int = 4) -> SourceSchedule:
    return SourceSchedule(
        source_id="cisa-kev",
        adapter_id="cisa-kev-feed",
        interval_seconds=900,
        lease_seconds=120,
        retry_policy=RetryPolicy(
            max_attempts=max_attempts,
            base_delay_seconds=10,
            max_delay_seconds=60,
            circuit_failure_threshold=threshold,
            circuit_reset_seconds=90,
        ),
    )


def _observation(job_id: UUID, *, payload: str = "same") -> RawObservation:
    return RawObservation(
        source_id="cisa-kev",
        adapter_id="cisa-kev-feed",
        adapter_version="1",
        collection_job_id=job_id,
        source_record_key="CVE-2026-12345",
        source_record_type="known_exploited_vulnerability",
        source_url="https://www.cisa.gov/kev.json",
        payload_hash_sha256=sha256(payload.encode()).hexdigest(),
        data_categories=frozenset({DataCategory.VULNERABILITY_METADATA}),
        collected_at=NOW,
        classification="public",
        retention_until=NOW + timedelta(days=30),
    )


def test_scheduler_is_idempotent_and_prevents_overlapping_active_jobs() -> None:
    factory = _factory()
    with factory.begin() as session:
        assert schedule_due_jobs(session, [_schedule()], now=NOW) == 1
        assert schedule_due_jobs(session, [_schedule()], now=NOW) == 0
        assert schedule_due_jobs(session, [_schedule()], now=NOW + timedelta(hours=1)) == 0
        count = session.scalar(select(func.count(CollectionJobRecord.id)))

    assert count == 1


def test_claim_heartbeat_complete_checkpoint_and_observation_deduplication() -> None:
    factory = _factory()
    schedule = _schedule()
    session = factory()
    try:
        assert schedule_due_jobs(session, [schedule], now=NOW) == 1
        claimed = claim_next_job(session, worker_id="worker-a", now=NOW)
        assert claimed is not None
        assert claim_next_job(session, worker_id="worker-b", now=NOW) is None
        renewed = heartbeat_job(
            session,
            claimed,
            now=NOW + timedelta(seconds=10),
            lease_seconds=120,
        )
        assert renewed == NOW + timedelta(seconds=130)
        written = complete_job(
            session,
            claimed,
            AdapterCollectionBatch(
                observations=(_observation(claimed.id),),
                checkpoint_payload={"etag": "v1"},
                not_modified=False,
            ),
            now=NOW + timedelta(seconds=20),
        )
        assert written == 1
        session.commit()

        assert schedule_due_jobs(session, [schedule], now=NOW + timedelta(minutes=15)) == 1
        second = claim_next_job(session, worker_id="worker-a", now=NOW + timedelta(minutes=15))
        assert second is not None
        written_again = complete_job(
            session,
            second,
            AdapterCollectionBatch(
                observations=(_observation(second.id),),
                checkpoint_payload={"etag": "v2"},
                not_modified=False,
            ),
            now=NOW + timedelta(minutes=15, seconds=10),
        )
        session.commit()

        checkpoint = session.get(
            CollectionCheckpointRecord,
            ("cisa-kev", "cisa-kev-feed"),
        )
        observations = session.scalar(select(func.count(RawObservationRecord.id)))
        assert written_again == 0
        assert checkpoint is not None
        assert checkpoint.version == 2
        assert checkpoint.payload == {"etag": "v2"}
        assert observations == 1
    finally:
        session.close()


def test_not_modified_job_advances_checkpoint_without_observations() -> None:
    factory = _factory()
    with factory.begin() as session:
        schedule_due_jobs(session, [_schedule()], now=NOW)
        claimed = claim_next_job(session, worker_id="worker", now=NOW)
        assert claimed is not None
        written = complete_job(
            session,
            claimed,
            AdapterCollectionBatch((), {"etag": "same"}, True),
            now=NOW + timedelta(seconds=1),
        )
        job = session.get(CollectionJobRecord, claimed.id)

    assert written == 0
    assert job is not None
    assert job.status == JobStatus.NOT_MODIFIED.value
    assert job.not_modified is True


def test_retry_opens_circuit_and_success_resets_it() -> None:
    factory = _factory()
    schedule = _schedule(threshold=2)
    session = factory()
    try:
        schedule_due_jobs(session, [schedule], now=NOW)
        first = claim_next_job(session, worker_id="worker", now=NOW)
        assert first is not None
        assert fail_job(
            session,
            first,
            now=NOW,
            error_code="timeout",
            error_message="temporary",
            retryable=True,
        ) is JobStatus.RETRY_SCHEDULED
        session.flush()

        second = claim_next_job(session, worker_id="worker", now=NOW + timedelta(seconds=10))
        assert second is not None
        assert fail_job(
            session,
            second,
            now=NOW + timedelta(seconds=10),
            error_code="timeout",
            error_message="temporary",
            retryable=True,
        ) is JobStatus.RETRY_SCHEDULED
        circuit = session.get(CollectionCircuitRecord, ("cisa-kev", "cisa-kev-feed"))
        assert circuit is not None
        assert circuit.state == CircuitState.OPEN.value
        assert circuit.reopen_at == NOW + timedelta(seconds=100)
        session.flush()

        assert claim_next_job(
            session,
            worker_id="worker",
            now=NOW + timedelta(seconds=99),
        ) is None
        third = claim_next_job(
            session,
            worker_id="worker",
            now=NOW + timedelta(seconds=100),
        )
        assert third is not None
        complete_job(
            session,
            third,
            AdapterCollectionBatch((), {"etag": "recovered"}, True),
            now=NOW + timedelta(seconds=101),
        )
        assert circuit.state == CircuitState.CLOSED.value
        assert circuit.consecutive_failures == 0
    finally:
        session.close()


def test_permanent_failure_creates_one_dead_letter() -> None:
    factory = _factory()
    with factory.begin() as session:
        schedule_due_jobs(session, [_schedule()], now=NOW)
        claimed = claim_next_job(session, worker_id="worker", now=NOW)
        assert claimed is not None
        status = fail_job(
            session,
            claimed,
            now=NOW + timedelta(seconds=1),
            error_code="schema_drift",
            error_message="invalid schema",
            retryable=False,
        )
        dead_letters = session.scalar(select(func.count(CollectionDeadLetterRecord.id)))

    assert status is JobStatus.DEAD_LETTERED
    assert dead_letters == 1


def test_expired_lease_is_recovered_without_advancing_checkpoint() -> None:
    factory = _factory()
    session = factory()
    try:
        schedule_due_jobs(session, [_schedule()], now=NOW)
        claimed = claim_next_job(session, worker_id="lost-worker", now=NOW)
        assert claimed is not None
        session.flush()
        assert recover_expired_leases(
            session,
            now=NOW + timedelta(seconds=121),
        ) == 1
        job = session.get(CollectionJobRecord, claimed.id)
        checkpoint = session.get(
            CollectionCheckpointRecord,
            ("cisa-kev", "cisa-kev-feed"),
        )
        assert job is not None
        assert job.status == JobStatus.RETRY_SCHEDULED.value
        assert checkpoint is None
    finally:
        session.close()


def test_completion_rollback_keeps_previous_cursor_and_observations() -> None:
    factory = _factory()
    session = factory()
    try:
        schedule_due_jobs(session, [_schedule()], now=NOW)
        claimed = claim_next_job(session, worker_id="worker", now=NOW)
        assert claimed is not None
        session.commit()

        complete_job(
            session,
            claimed,
            AdapterCollectionBatch(
                (_observation(claimed.id),),
                {"etag": "must-not-commit"},
                False,
            ),
            now=NOW + timedelta(seconds=1),
        )
        session.rollback()

        assert session.get(
            CollectionCheckpointRecord,
            ("cisa-kev", "cisa-kev-feed"),
        ) is None
        assert session.scalar(select(func.count(RawObservationRecord.id))) == 0
        job = session.get(CollectionJobRecord, claimed.id)
        assert job is not None
        assert job.status == JobStatus.RUNNING.value
    finally:
        session.close()


def test_lost_or_invalid_lease_is_rejected() -> None:
    factory = _factory()
    session = factory()
    try:
        schedule_due_jobs(session, [_schedule()], now=NOW)
        claimed = claim_next_job(session, worker_id="worker", now=NOW)
        assert claimed is not None
        record = session.get(CollectionJobRecord, claimed.id)
        assert record is not None
        record.lease_owner = "other-worker"
        with pytest.raises(LeaseLostError, match="another worker"):
            heartbeat_job(session, claimed, now=NOW, lease_seconds=10)
        with pytest.raises(ValueError, match="lease_seconds"):
            heartbeat_job(session, claimed, now=NOW, lease_seconds=0)
    finally:
        session.close()

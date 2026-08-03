from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    ClaimedJob,
)
from cip.modules.collection_orchestration.domain.models import (
    CircuitState,
    CollectionJob,
    JobStatus,
)
from cip.modules.collection_orchestration.infrastructure.models import (
    CollectionCheckpointRecord,
    CollectionCircuitRecord,
    CollectionDeadLetterRecord,
    CollectionJobRecord,
)
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.raw_observations.infrastructure.models import RawObservationRecord
from cip.shared.kernel.time import require_aware_utc

_ACTIVE_STATUSES = (
    JobStatus.PENDING.value,
    JobStatus.RUNNING.value,
    JobStatus.RETRY_SCHEDULED.value,
)


class LeaseLostError(RuntimeError):
    """A worker attempted to update a job after losing ownership of its lease."""


def has_active_job(session: Session, *, source_id: str, adapter_id: str) -> bool:
    statement = select(CollectionJobRecord.id).where(
        CollectionJobRecord.source_id == source_id,
        CollectionJobRecord.adapter_id == adapter_id,
        CollectionJobRecord.status.in_(_ACTIVE_STATUSES),
    )
    return session.scalar(statement.limit(1)) is not None


def enqueue_job(session: Session, job: CollectionJob) -> bool:
    values = {
        "id": job.id,
        "source_id": job.source_id,
        "adapter_id": job.adapter_id,
        "status": job.status.value,
        "scheduled_for": job.scheduled_for,
        "available_at": job.available_at,
        "idempotency_key": job.idempotency_key,
        "attempt": job.attempt,
        "lease_seconds": job.lease_seconds,
        "max_attempts": job.max_attempts,
        "base_delay_seconds": job.base_delay_seconds,
        "max_delay_seconds": job.max_delay_seconds,
        "circuit_failure_threshold": job.circuit_failure_threshold,
        "circuit_reset_seconds": job.circuit_reset_seconds,
        "created_at": job.created_at,
        "observations_written": 0,
        "not_modified": False,
    }
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        postgres_statement = postgresql_insert(CollectionJobRecord).values(**values)
        postgres_statement = postgres_statement.on_conflict_do_nothing(
            index_elements=["idempotency_key"]
        )
        result = session.execute(postgres_statement)
        return bool(getattr(result, "rowcount", 0))
    if dialect == "sqlite":
        sqlite_statement = sqlite_insert(CollectionJobRecord).values(**values)
        sqlite_statement = sqlite_statement.on_conflict_do_nothing(
            index_elements=["idempotency_key"]
        )
        result = session.execute(sqlite_statement)
        return bool(getattr(result, "rowcount", 0))
    if session.scalar(
        select(CollectionJobRecord.id).where(
            CollectionJobRecord.idempotency_key == job.idempotency_key
        )
    ):
        return False
    session.add(CollectionJobRecord(**values))
    return True


def claim_next_job(
    session: Session,
    *,
    worker_id: str,
    now: datetime,
) -> ClaimedJob | None:
    current = require_aware_utc(now, field_name="now")
    if not worker_id.strip():
        raise ValueError("worker_id is required")
    recover_expired_leases(session, now=current)
    session.flush()
    statement = (
        select(CollectionJobRecord)
        .where(
            CollectionJobRecord.status.in_(
                (JobStatus.PENDING.value, JobStatus.RETRY_SCHEDULED.value)
            ),
            CollectionJobRecord.available_at <= current,
        )
        .order_by(CollectionJobRecord.scheduled_for, CollectionJobRecord.created_at)
        .with_for_update(skip_locked=True)
        .limit(20)
    )
    for record in session.scalars(statement):
        if not _circuit_allows_claim(session, record=record, now=current):
            continue
        if record.attempt >= record.max_attempts:
            _dead_letter(
                session,
                record=record,
                now=current,
                error_code="attempt_limit_reached",
                error_message="job reached its configured attempt limit before claim",
            )
            continue
        record.status = JobStatus.RUNNING.value
        record.attempt += 1
        record.started_at = record.started_at or current
        record.lease_owner = worker_id
        record.lease_expires_at = current + timedelta(seconds=record.lease_seconds)
        record.error_code = None
        record.error_message = None
        checkpoint = session.get(
            CollectionCheckpointRecord,
            (record.source_id, record.adapter_id),
        )
        return ClaimedJob(
            id=record.id,
            source_id=record.source_id,
            adapter_id=record.adapter_id,
            attempt=record.attempt,
            lease_owner=worker_id,
            lease_expires_at=record.lease_expires_at,
            max_attempts=record.max_attempts,
            base_delay_seconds=record.base_delay_seconds,
            max_delay_seconds=record.max_delay_seconds,
            circuit_failure_threshold=record.circuit_failure_threshold,
            circuit_reset_seconds=record.circuit_reset_seconds,
            checkpoint_payload=dict(checkpoint.payload) if checkpoint else None,
        )
    return None


def heartbeat_job(
    session: Session,
    claimed: ClaimedJob,
    *,
    now: datetime,
    lease_seconds: int,
) -> datetime:
    current = require_aware_utc(now, field_name="now")
    if lease_seconds < 1:
        raise ValueError("lease_seconds must be positive")
    record = _owned_running_job(session, claimed=claimed, now=current)
    record.lease_expires_at = current + timedelta(seconds=lease_seconds)
    return record.lease_expires_at


def complete_job(
    session: Session,
    claimed: ClaimedJob,
    batch: AdapterCollectionBatch,
    *,
    now: datetime,
) -> int:
    current = require_aware_utc(now, field_name="now")
    record = _owned_running_job(session, claimed=claimed, now=current)
    written = _insert_observations(session, batch.observations)
    _advance_checkpoint(
        session,
        claimed=claimed,
        payload=batch.checkpoint_payload,
        observations=batch.observations,
        now=current,
    )
    record.status = (
        JobStatus.NOT_MODIFIED.value if batch.not_modified else JobStatus.SUCCEEDED.value
    )
    record.finished_at = current
    record.lease_owner = None
    record.lease_expires_at = None
    record.observations_written = written
    record.not_modified = batch.not_modified
    record.error_code = None
    record.error_message = None
    _reset_circuit(session, source_id=record.source_id, adapter_id=record.adapter_id, now=current)
    return written


def fail_job(
    session: Session,
    claimed: ClaimedJob,
    *,
    now: datetime,
    error_code: str,
    error_message: str,
    retryable: bool,
) -> JobStatus:
    current = require_aware_utc(now, field_name="now")
    record = _owned_running_job(session, claimed=claimed, now=current, require_unexpired=False)
    return _record_failure(
        session,
        record=record,
        now=current,
        error_code=error_code,
        error_message=error_message,
        retryable=retryable,
    )


def recover_expired_leases(session: Session, *, now: datetime) -> int:
    current = require_aware_utc(now, field_name="now")
    statement = (
        select(CollectionJobRecord)
        .where(
            CollectionJobRecord.status == JobStatus.RUNNING.value,
            CollectionJobRecord.lease_expires_at.is_not(None),
            CollectionJobRecord.lease_expires_at <= current,
        )
        .with_for_update(skip_locked=True)
    )
    recovered = 0
    for record in session.scalars(statement):
        _record_failure(
            session,
            record=record,
            now=current,
            error_code="lease_expired",
            error_message="worker lease expired before completion",
            retryable=True,
        )
        recovered += 1
    return recovered


def _record_failure(
    session: Session,
    *,
    record: CollectionJobRecord,
    now: datetime,
    error_code: str,
    error_message: str,
    retryable: bool,
) -> JobStatus:
    code = error_code.strip() or "collection_error"
    message = (error_message.strip() or code)[:4_000]
    circuit = _register_circuit_failure(session, record=record, now=now, error_code=code)
    if retryable and record.attempt < record.max_attempts:
        delay_seconds = min(
            record.base_delay_seconds * (2 ** max(record.attempt - 1, 0)),
            record.max_delay_seconds,
        )
        available_at = now + timedelta(seconds=delay_seconds)
        if circuit.state == CircuitState.OPEN.value and circuit.reopen_at is not None:
            available_at = max(available_at, _database_utc(circuit.reopen_at))
        record.status = JobStatus.RETRY_SCHEDULED.value
        record.available_at = available_at
        record.lease_owner = None
        record.lease_expires_at = None
        record.error_code = code
        record.error_message = message
        return JobStatus.RETRY_SCHEDULED
    _dead_letter(
        session,
        record=record,
        now=now,
        error_code=code,
        error_message=message,
    )
    return JobStatus.DEAD_LETTERED


def _owned_running_job(
    session: Session,
    *,
    claimed: ClaimedJob,
    now: datetime,
    require_unexpired: bool = True,
) -> CollectionJobRecord:
    record = session.get(CollectionJobRecord, claimed.id, with_for_update=True)
    if record is None or record.status != JobStatus.RUNNING.value:
        raise LeaseLostError("job is no longer running")
    if record.lease_owner != claimed.lease_owner:
        raise LeaseLostError("job lease is owned by another worker")
    lease_expires_at = (
        _database_utc(record.lease_expires_at)
        if record.lease_expires_at is not None
        else None
    )
    if require_unexpired and (lease_expires_at is None or lease_expires_at <= now):
        raise LeaseLostError("job lease has expired")
    return record


def _circuit_allows_claim(
    session: Session,
    *,
    record: CollectionJobRecord,
    now: datetime,
) -> bool:
    circuit = session.get(
        CollectionCircuitRecord,
        (record.source_id, record.adapter_id),
        with_for_update=True,
    )
    if circuit is None or circuit.state == CircuitState.CLOSED.value:
        return True
    reopen_at = _database_utc(circuit.reopen_at) if circuit.reopen_at is not None else None
    if reopen_at is not None and reopen_at > now:
        record.available_at = max(_database_utc(record.available_at), reopen_at)
        return False
    circuit.state = CircuitState.HALF_OPEN.value
    circuit.updated_at = now
    return True


def _register_circuit_failure(
    session: Session,
    *,
    record: CollectionJobRecord,
    now: datetime,
    error_code: str,
) -> CollectionCircuitRecord:
    circuit = session.get(
        CollectionCircuitRecord,
        (record.source_id, record.adapter_id),
        with_for_update=True,
    )
    if circuit is None:
        circuit = CollectionCircuitRecord(
            source_id=record.source_id,
            adapter_id=record.adapter_id,
            state=CircuitState.CLOSED.value,
            consecutive_failures=0,
            updated_at=now,
        )
        session.add(circuit)
    circuit.consecutive_failures += 1
    circuit.last_error_code = error_code
    circuit.updated_at = now
    if circuit.consecutive_failures >= record.circuit_failure_threshold:
        circuit.state = CircuitState.OPEN.value
        circuit.opened_at = now
        circuit.reopen_at = now + timedelta(seconds=record.circuit_reset_seconds)
    else:
        circuit.state = CircuitState.CLOSED.value
        circuit.opened_at = None
        circuit.reopen_at = None
    return circuit


def _reset_circuit(
    session: Session,
    *,
    source_id: str,
    adapter_id: str,
    now: datetime,
) -> None:
    circuit = session.get(
        CollectionCircuitRecord,
        (source_id, adapter_id),
        with_for_update=True,
    )
    if circuit is None:
        return
    circuit.state = CircuitState.CLOSED.value
    circuit.consecutive_failures = 0
    circuit.opened_at = None
    circuit.reopen_at = None
    circuit.last_error_code = None
    circuit.updated_at = now


def _dead_letter(
    session: Session,
    *,
    record: CollectionJobRecord,
    now: datetime,
    error_code: str,
    error_message: str,
) -> None:
    checkpoint = session.get(
        CollectionCheckpointRecord,
        (record.source_id, record.adapter_id),
    )
    existing = session.scalar(
        select(CollectionDeadLetterRecord.id).where(
            CollectionDeadLetterRecord.job_id == record.id
        )
    )
    if existing is None:
        session.add(
            CollectionDeadLetterRecord(
                id=uuid4(),
                job_id=record.id,
                source_id=record.source_id,
                adapter_id=record.adapter_id,
                failed_at=now,
                attempt=record.attempt,
                error_code=error_code,
                error_message=error_message,
                checkpoint_snapshot=dict(checkpoint.payload) if checkpoint else None,
            )
        )
    record.status = JobStatus.DEAD_LETTERED.value
    record.finished_at = now
    record.lease_owner = None
    record.lease_expires_at = None
    record.error_code = error_code
    record.error_message = error_message
    session.flush()


def _advance_checkpoint(
    session: Session,
    *,
    claimed: ClaimedJob,
    payload: Mapping[str, object],
    observations: Sequence[RawObservation],
    now: datetime,
) -> None:
    checkpoint = session.get(
        CollectionCheckpointRecord,
        (claimed.source_id, claimed.adapter_id),
        with_for_update=True,
    )
    last_observation_at = max(
        (observation.collected_at for observation in observations),
        default=None,
    )
    if checkpoint is None:
        session.add(
            CollectionCheckpointRecord(
                source_id=claimed.source_id,
                adapter_id=claimed.adapter_id,
                payload=dict(payload),
                version=1,
                updated_at=now,
                last_success_at=now,
                last_observation_at=last_observation_at,
            )
        )
        return
    checkpoint.payload = dict(payload)
    checkpoint.version += 1
    checkpoint.updated_at = now
    checkpoint.last_success_at = now
    if last_observation_at is not None:
        checkpoint.last_observation_at = last_observation_at


def _insert_observations(
    session: Session,
    observations: Sequence[RawObservation],
) -> int:
    if not observations:
        return 0
    values = [_observation_values(observation) for observation in observations]
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        postgres_statement = postgresql_insert(RawObservationRecord).values(values)
        postgres_statement = postgres_statement.on_conflict_do_nothing(
            constraint="uq_raw_observation_deduplication"
        )
        result = session.execute(postgres_statement)
        return int(getattr(result, "rowcount", 0) or 0)
    if dialect == "sqlite":
        sqlite_statement = sqlite_insert(RawObservationRecord).values(values)
        sqlite_statement = sqlite_statement.on_conflict_do_nothing(
            index_elements=["source_id", "source_record_key", "payload_hash_sha256"]
        )
        result = session.execute(sqlite_statement)
        return int(getattr(result, "rowcount", 0) or 0)
    written = 0
    for observation, record_values in zip(observations, values, strict=True):
        existing = session.scalar(
            select(RawObservationRecord.id).where(
                RawObservationRecord.source_id == observation.source_id,
                RawObservationRecord.source_record_key == observation.source_record_key,
                RawObservationRecord.payload_hash_sha256 == observation.payload_hash_sha256,
            )
        )
        if existing is None:
            session.add(RawObservationRecord(**record_values))
            written += 1
    return written


def _observation_values(observation: RawObservation) -> dict[str, Any]:
    return {
        "id": observation.id,
        "source_id": observation.source_id,
        "adapter_id": observation.adapter_id,
        "adapter_version": observation.adapter_version,
        "collection_job_id": observation.collection_job_id,
        "source_record_key": observation.source_record_key,
        "source_record_type": observation.source_record_type,
        "source_url": observation.source_url,
        "collected_at": observation.collected_at,
        "observed_at": observation.observed_at,
        "published_at": observation.published_at,
        "source_updated_at": observation.source_updated_at,
        "payload_reference": observation.payload_reference,
        "payload_hash_sha256": observation.payload_hash_sha256,
        "schema_fingerprint": observation.schema_fingerprint,
        "content_language": observation.content_language,
        "data_categories": sorted(category.value for category in observation.data_categories),
        "classification": observation.classification,
        "retention_until": observation.retention_until,
    }


def _database_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

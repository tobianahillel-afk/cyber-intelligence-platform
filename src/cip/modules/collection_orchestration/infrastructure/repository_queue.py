from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from cip.modules.collection_orchestration.application.ports import ClaimedJob
from cip.modules.collection_orchestration.domain.models import CollectionJob, JobStatus
from cip.modules.collection_orchestration.infrastructure.models import (
    CollectionCheckpointRecord,
    CollectionJobRecord,
)
from cip.modules.collection_orchestration.infrastructure.repository_circuits import (
    circuit_allows_claim,
)
from cip.modules.collection_orchestration.infrastructure.repository_common import (
    owned_running_job,
)
from cip.modules.collection_orchestration.infrastructure.repository_failures import (
    dead_letter_job,
    recover_expired_leases,
)
from cip.shared.kernel.time import require_aware_utc

_ACTIVE_STATUSES = (
    JobStatus.PENDING.value,
    JobStatus.RUNNING.value,
    JobStatus.RETRY_SCHEDULED.value,
    JobStatus.AWAITING_HUMAN_CHECKPOINT.value,
)


def has_active_job(session: Session, *, source_id: str, adapter_id: str) -> bool:
    statement = select(CollectionJobRecord.id).where(
        CollectionJobRecord.source_id == source_id,
        CollectionJobRecord.adapter_id == adapter_id,
        CollectionJobRecord.status.in_(_ACTIVE_STATUSES),
    )
    return session.scalar(statement.limit(1)) is not None


def enqueue_job(session: Session, job: CollectionJob) -> bool:
    values = _job_values(job)
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        postgres_statement = postgresql_insert(CollectionJobRecord).values(**values)
        result = session.execute(
            postgres_statement.on_conflict_do_nothing(
                index_elements=["idempotency_key"]
            )
        )
        return bool(getattr(result, "rowcount", 0))
    if dialect == "sqlite":
        sqlite_statement = sqlite_insert(CollectionJobRecord).values(**values)
        result = session.execute(
            sqlite_statement.on_conflict_do_nothing(
                index_elements=["idempotency_key"]
            )
        )
        return bool(getattr(result, "rowcount", 0))
    return _enqueue_portable(session, job, values)


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
    for record in session.scalars(_claim_statement(current)):
        if not circuit_allows_claim(session, record=record, now=current):
            continue
        if not record.human_resume_pending and record.attempt >= record.max_attempts:
            dead_letter_job(
                session,
                record=record,
                now=current,
                error_code="attempt_limit_reached",
                error_message="job reached its configured attempt limit before claim",
            )
            continue
        return _claim_record(session, record=record, worker_id=worker_id, now=current)
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
    record = owned_running_job(session, claimed=claimed, now=current)
    lease_expires_at = current + timedelta(seconds=lease_seconds)
    record.lease_expires_at = lease_expires_at
    return lease_expires_at


def _claim_statement(now: datetime) -> Select[tuple[CollectionJobRecord]]:
    return (
        select(CollectionJobRecord)
        .where(
            CollectionJobRecord.status.in_(
                (JobStatus.PENDING.value, JobStatus.RETRY_SCHEDULED.value)
            ),
            CollectionJobRecord.available_at <= now,
        )
        .order_by(CollectionJobRecord.scheduled_for, CollectionJobRecord.created_at)
        .with_for_update(skip_locked=True)
        .limit(20)
    )


def _claim_record(
    session: Session,
    *,
    record: CollectionJobRecord,
    worker_id: str,
    now: datetime,
) -> ClaimedJob:
    lease_expires_at = now + timedelta(seconds=record.lease_seconds)
    record.status = JobStatus.RUNNING.value
    if not record.human_resume_pending:
        record.attempt += 1
    record.human_resume_pending = False
    record.started_at = record.started_at or now
    record.lease_owner = worker_id
    record.lease_expires_at = lease_expires_at
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
        lease_expires_at=lease_expires_at,
        max_attempts=record.max_attempts,
        base_delay_seconds=record.base_delay_seconds,
        max_delay_seconds=record.max_delay_seconds,
        circuit_failure_threshold=record.circuit_failure_threshold,
        circuit_reset_seconds=record.circuit_reset_seconds,
        checkpoint_payload=dict(checkpoint.payload) if checkpoint else None,
    )


def _enqueue_portable(
    session: Session,
    job: CollectionJob,
    values: dict[str, object],
) -> bool:
    existing = session.scalar(
        select(CollectionJobRecord.id).where(
            CollectionJobRecord.idempotency_key == job.idempotency_key
        )
    )
    if existing is not None:
        return False
    session.add(CollectionJobRecord(**values))
    return True


def _job_values(job: CollectionJob) -> dict[str, object]:
    return {
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
        "human_resume_pending": False,
        "observations_written": 0,
        "not_modified": False,
    }

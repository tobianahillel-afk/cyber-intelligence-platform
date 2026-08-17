from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from cip.modules.collection_orchestration.application.ports import ClaimedJob
from cip.modules.collection_orchestration.domain.models import CollectionJob, JobStatus
from cip.modules.collection_orchestration.infrastructure.models import CollectionJobRecord
from cip.modules.collection_orchestration.infrastructure.repository_circuits import (
    circuit_allows_claim,
)
from cip.modules.collection_orchestration.infrastructure.repository_common import database_utc
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
    record = CollectionJobRecord(
        id=job.id,
        source_id=job.source_id,
        adapter_id=job.adapter_id,
        status=job.status.value,
        scheduled_for=job.scheduled_for,
        available_at=job.available_at,
        idempotency_key=job.idempotency_key,
        attempt=job.attempt,
        lease_seconds=job.lease_seconds,
        max_attempts=job.max_attempts,
        base_delay_seconds=job.base_delay_seconds,
        max_delay_seconds=job.max_delay_seconds,
        circuit_failure_threshold=job.circuit_failure_threshold,
        circuit_reset_seconds=job.circuit_reset_seconds,
        created_at=job.created_at,
        human_resume_pending=False,
        observations_written=0,
        not_modified=False,
    )
    nested = session.begin_nested()
    try:
        session.add(record)
        session.flush()
        nested.commit()
    except IntegrityError:
        nested.rollback()
        return False
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
    candidates = session.scalars(_claim_statement(current)).all()
    for record in candidates:
        if not circuit_allows_claim(
            session,
            source_id=record.source_id,
            adapter_id=record.adapter_id,
            now=current,
        ):
            continue
        return _claim_record(record, worker_id=worker_id, now=current)
    return None


def _claim_statement(now: datetime) -> Select[tuple[CollectionJobRecord]]:
    return (
        select(CollectionJobRecord)
        .where(
            CollectionJobRecord.status.in_(
                (JobStatus.PENDING.value, JobStatus.RETRY_SCHEDULED.value)
            ),
            CollectionJobRecord.available_at <= now,
            or_(
                CollectionJobRecord.lease_expires_at.is_(None),
                CollectionJobRecord.lease_expires_at <= now,
            ),
        )
        .order_by(CollectionJobRecord.available_at, CollectionJobRecord.scheduled_for)
        .limit(50)
        .with_for_update(skip_locked=True)
    )


def _claim_record(
    record: CollectionJobRecord,
    *,
    worker_id: str,
    now: datetime,
) -> ClaimedJob:
    resumed_from_human = record.human_resume_pending
    if not resumed_from_human:
        record.attempt += 1
    record.human_resume_pending = False
    record.status = JobStatus.RUNNING.value
    record.started_at = now
    record.finished_at = None
    record.lease_owner = worker_id
    record.lease_expires_at = now + timedelta(seconds=record.lease_seconds)
    record.error_code = None
    record.error_message = None
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
        checkpoint_payload=None,
    )


def heartbeat_job(
    session: Session,
    claimed: ClaimedJob,
    *,
    now: datetime,
    lease_seconds: int,
) -> datetime:
    from cip.modules.collection_orchestration.infrastructure.repository_common import (
        LeaseLostError,
        owned_running_job,
    )

    current = require_aware_utc(now, field_name="now")
    if lease_seconds < 1:
        raise ValueError("lease_seconds must be positive")
    record = owned_running_job(session, claimed=claimed, now=current)
    record.lease_expires_at = current + timedelta(seconds=lease_seconds)
    if record.lease_expires_at is None:  # pragma: no cover - defensive typing guard
        raise LeaseLostError("job lease could not be renewed")
    return database_utc(record.lease_expires_at)


def recover_expired_leases(session: Session, *, now: datetime) -> int:
    current = require_aware_utc(now, field_name="now")
    statement = (
        select(CollectionJobRecord)
        .where(
            and_(
                CollectionJobRecord.status == JobStatus.RUNNING.value,
                CollectionJobRecord.lease_expires_at.is_not(None),
                CollectionJobRecord.lease_expires_at <= current,
            )
        )
        .with_for_update(skip_locked=True)
    )
    recovered = 0
    for record in session.scalars(statement):
        record.status = JobStatus.RETRY_SCHEDULED.value
        record.available_at = current
        record.lease_owner = None
        record.lease_expires_at = None
        record.human_resume_pending = False
        record.error_code = "lease_expired"
        record.error_message = "worker lease expired before completion"
        recovered += 1
    return recovered


def cancel_queued_job(
    session: Session,
    *,
    job_id: UUID,
    now: datetime,
    reason: str,
) -> bool:
    current = require_aware_utc(now, field_name="now")
    normalized_reason = reason.strip()
    if not normalized_reason or len(normalized_reason) > 100:
        raise ValueError("cancellation reason must be non-empty and at most 100 characters")
    record = session.get(CollectionJobRecord, job_id, with_for_update=True)
    if record is None:
        return False
    if record.status not in {
        JobStatus.PENDING.value,
        JobStatus.RETRY_SCHEDULED.value,
    }:
        return False
    record.status = JobStatus.CANCELLED.value
    record.finished_at = current
    record.lease_owner = None
    record.lease_expires_at = None
    record.human_resume_pending = False
    record.error_code = normalized_reason
    record.error_message = "collection cancelled before adapter execution"
    return True

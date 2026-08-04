from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.collection_orchestration.application.ports import ClaimedJob
from cip.modules.collection_orchestration.domain.models import CircuitState, JobStatus
from cip.modules.collection_orchestration.infrastructure.models import (
    CollectionCheckpointRecord,
    CollectionDeadLetterRecord,
    CollectionJobRecord,
)
from cip.modules.collection_orchestration.infrastructure.repository_circuits import (
    register_circuit_failure,
)
from cip.modules.collection_orchestration.infrastructure.repository_common import (
    database_utc,
    owned_running_job,
)
from cip.shared.kernel.time import require_aware_utc


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
    record = owned_running_job(
        session,
        claimed=claimed,
        now=current,
        require_unexpired=False,
    )
    return record_failure(
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
        record_failure(
            session,
            record=record,
            now=current,
            error_code="lease_expired",
            error_message="worker lease expired before completion",
            retryable=True,
        )
        recovered += 1
    return recovered


def record_failure(
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
    circuit = register_circuit_failure(
        session,
        record=record,
        now=now,
        error_code=code,
    )
    if retryable and record.attempt < record.max_attempts:
        _schedule_retry(
            record,
            circuit_state=circuit.state,
            reopen_at=circuit.reopen_at,
            now=now,
        )
        record.error_code = code
        record.error_message = message
        return JobStatus.RETRY_SCHEDULED
    dead_letter_job(
        session,
        record=record,
        now=now,
        error_code=code,
        error_message=message,
    )
    return JobStatus.DEAD_LETTERED


def dead_letter_job(
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


def _schedule_retry(
    record: CollectionJobRecord,
    *,
    circuit_state: str,
    reopen_at: datetime | None,
    now: datetime,
) -> None:
    delay_seconds = min(
        record.base_delay_seconds * (2 ** max(record.attempt - 1, 0)),
        record.max_delay_seconds,
    )
    available_at = now + timedelta(seconds=delay_seconds)
    if circuit_state == CircuitState.OPEN.value and reopen_at is not None:
        available_at = max(available_at, database_utc(reopen_at))
    record.status = JobStatus.RETRY_SCHEDULED.value
    record.available_at = available_at
    record.lease_owner = None
    record.lease_expires_at = None

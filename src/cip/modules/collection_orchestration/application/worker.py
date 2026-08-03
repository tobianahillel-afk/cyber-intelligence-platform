from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from cip.modules.collection_orchestration.application.ports import (
    AdapterExecutionError,
    CollectionAdapter,
)
from cip.modules.collection_orchestration.domain.models import JobStatus
from cip.modules.collection_orchestration.infrastructure.repository import (
    LeaseLostError,
    claim_next_job,
    complete_job,
    fail_job,
)
from cip.modules.data_governance.domain.retention import RetentionPolicy
from cip.shared.kernel.time import utc_now
from cip.shared.persistence.session import session_scope


class WorkerStatus(StrEnum):
    IDLE = "idle"
    SUCCEEDED = "succeeded"
    NOT_MODIFIED = "not_modified"
    RETRY_SCHEDULED = "retry_scheduled"
    DEAD_LETTERED = "dead_lettered"
    LEASE_LOST = "lease_lost"


@dataclass(frozen=True, slots=True)
class WorkerOutcome:
    status: WorkerStatus
    job_id: UUID | None = None
    observations_written: int = 0
    error_code: str | None = None


def run_worker_once(
    factory: sessionmaker[Session],
    *,
    worker_id: str,
    adapters: Mapping[tuple[str, str], CollectionAdapter],
    retention_policy: RetentionPolicy,
    clock: Callable[[], object] = utc_now,
) -> WorkerOutcome:
    claim_time = _read_clock(clock)
    with session_scope(factory) as session:
        claimed = claim_next_job(session, worker_id=worker_id, now=claim_time)
    if claimed is None:
        return WorkerOutcome(WorkerStatus.IDLE)

    adapter = adapters.get((claimed.source_id, claimed.adapter_id))
    if adapter is None:
        return _record_failure(
            factory,
            claimed=claimed,
            clock=clock,
            error_code="adapter_not_registered",
            error_message="no adapter is registered for the claimed source",
            retryable=False,
        )

    retention_until = retention_policy.retention_deadline(
        adapter.data_category,
        claim_time,
    )
    try:
        batch = adapter.collect(
            collection_job_id=claimed.id,
            checkpoint_payload=claimed.checkpoint_payload,
            collected_at=claim_time,
            retention_until=retention_until,
        )
    except AdapterExecutionError as exc:
        return _record_failure(
            factory,
            claimed=claimed,
            clock=clock,
            error_code=exc.error_code,
            error_message=str(exc),
            retryable=exc.retryable,
        )
    except Exception as exc:
        return _record_failure(
            factory,
            claimed=claimed,
            clock=clock,
            error_code="unexpected_adapter_error",
            error_message=str(exc) or type(exc).__name__,
            retryable=True,
        )

    try:
        with session_scope(factory) as session:
            written = complete_job(
                session,
                claimed,
                batch,
                now=_read_clock(clock),
            )
    except LeaseLostError:
        return WorkerOutcome(
            WorkerStatus.LEASE_LOST,
            job_id=claimed.id,
            error_code="lease_lost",
        )
    return WorkerOutcome(
        WorkerStatus.NOT_MODIFIED if batch.not_modified else WorkerStatus.SUCCEEDED,
        job_id=claimed.id,
        observations_written=written,
    )


def _record_failure(
    factory: sessionmaker[Session],
    *,
    claimed: object,
    clock: Callable[[], object],
    error_code: str,
    error_message: str,
    retryable: bool,
) -> WorkerOutcome:
    from cip.modules.collection_orchestration.application.ports import ClaimedJob

    if not isinstance(claimed, ClaimedJob):
        raise TypeError("claimed must be a ClaimedJob")
    try:
        with session_scope(factory) as session:
            status = fail_job(
                session,
                claimed,
                now=_read_clock(clock),
                error_code=error_code,
                error_message=error_message,
                retryable=retryable,
            )
    except LeaseLostError:
        return WorkerOutcome(
            WorkerStatus.LEASE_LOST,
            job_id=claimed.id,
            error_code="lease_lost",
        )
    return WorkerOutcome(
        _worker_status(status),
        job_id=claimed.id,
        error_code=error_code,
    )


def _worker_status(status: JobStatus) -> WorkerStatus:
    if status is JobStatus.RETRY_SCHEDULED:
        return WorkerStatus.RETRY_SCHEDULED
    if status is JobStatus.DEAD_LETTERED:
        return WorkerStatus.DEAD_LETTERED
    raise ValueError(f"unsupported failure status: {status.value}")


def _read_clock(clock: Callable[[], object]):
    from datetime import datetime

    value = clock()
    if not isinstance(value, datetime):
        raise TypeError("clock must return datetime")
    return value

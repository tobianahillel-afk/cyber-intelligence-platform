from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
    AdapterPartialExecutionError,
    ClaimedJob,
    CollectionAdapter,
)
from cip.modules.collection_orchestration.application.worker_persistence import (
    persist_batch_projections,
    record_failure_health,
    record_success_health,
)
from cip.modules.collection_orchestration.domain.models import JobStatus
from cip.modules.collection_orchestration.infrastructure.repository import (
    LeaseLostError,
    cancel_claimed_job,
    claim_next_job,
    complete_job,
    fail_job,
    persist_partial_progress,
)
from cip.modules.data_governance.domain.retention import RetentionPolicy
from cip.modules.source_portfolio.application.execution import source_execution_allowed
from cip.modules.source_portfolio.application.service import (
    SourceExecutionMode,
    SourceValueEvent,
    record_source_value_event,
)
from cip.shared.kernel.time import require_aware_utc, utc_now
from cip.shared.persistence.session import session_scope


class WorkerStatus(StrEnum):
    IDLE = "idle"
    SUCCEEDED = "succeeded"
    NOT_MODIFIED = "not_modified"
    RETRY_SCHEDULED = "retry_scheduled"
    DEAD_LETTERED = "dead_lettered"
    CANCELLED = "cancelled"
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
    clock: Callable[[], datetime] = utc_now,
) -> WorkerOutcome:
    claim_time = _read_clock(clock)
    with session_scope(factory) as session:
        claimed = claim_next_job(session, worker_id=worker_id, now=claim_time)
        if claimed is not None and not source_execution_allowed(
            session,
            claimed.source_id,
            now=claim_time,
        ):
            cancel_claimed_job(
                session,
                claimed,
                now=claim_time,
                reason="source_execution_disabled",
            )
            return WorkerOutcome(
                WorkerStatus.CANCELLED,
                job_id=claimed.id,
                error_code="source_execution_disabled",
            )
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
    except AdapterPartialExecutionError as exc:
        return _record_partial_failure(
            factory,
            claimed=claimed,
            batch=exc.batch,
            clock=clock,
            error_code=exc.error_code,
            error_message=str(exc),
            retryable=exc.retryable,
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
        written = _complete_success(
            factory,
            claimed=claimed,
            batch=batch,
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


def _complete_success(
    factory: sessionmaker[Session],
    *,
    claimed: ClaimedJob,
    batch: AdapterCollectionBatch,
    now: datetime,
) -> int:
    with session_scope(factory) as session:
        written = complete_job(session, claimed, batch, now=now)
        persist_batch_projections(session, batch, now=now)
        record_success_health(session, claimed.source_id, batch, now=now)
        record_source_value_event(
            session,
            SourceValueEvent(
                source_id=claimed.source_id,
                execution_id=claimed.id,
                execution_mode=SourceExecutionMode.INCREMENTAL,
                observations_written=written,
                commercial_projections=(
                    len(batch.commercial_projections) + len(batch.procurement_projections)
                ),
                identity_projections=len(batch.identity_projections),
                request_cost=batch.request_cost,
                not_modified=batch.not_modified,
                occurred_at=now,
            ),
        )
    return written


def _record_partial_failure(
    factory: sessionmaker[Session],
    *,
    claimed: ClaimedJob,
    batch: AdapterCollectionBatch,
    clock: Callable[[], datetime],
    error_code: str,
    error_message: str,
    retryable: bool,
) -> WorkerOutcome:
    try:
        with session_scope(factory) as session:
            failure_time = _read_clock(clock)
            written = persist_partial_progress(
                session,
                claimed,
                batch,
                now=failure_time,
            )
            persist_batch_projections(session, batch, now=failure_time)
            status = fail_job(
                session,
                claimed,
                now=failure_time,
                error_code=error_code,
                error_message=error_message,
                retryable=retryable,
            )
            record_failure_health(
                session,
                claimed.source_id,
                error_code=error_code,
                now=failure_time,
                batch=batch,
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
        observations_written=written,
        error_code=error_code,
    )


def _record_failure(
    factory: sessionmaker[Session],
    *,
    claimed: ClaimedJob,
    clock: Callable[[], datetime],
    error_code: str,
    error_message: str,
    retryable: bool,
) -> WorkerOutcome:
    try:
        with session_scope(factory) as session:
            failure_time = _read_clock(clock)
            status = fail_job(
                session,
                claimed,
                now=failure_time,
                error_code=error_code,
                error_message=error_message,
                retryable=retryable,
            )
            record_failure_health(
                session,
                claimed.source_id,
                error_code=error_code,
                now=failure_time,
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


def _read_clock(clock: Callable[[], datetime]) -> datetime:
    return require_aware_utc(clock(), field_name="clock")

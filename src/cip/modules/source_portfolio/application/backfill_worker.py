from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from cip.modules.collection_orchestration.application.ports import (
    AdapterExecutionError,
    CollectionAdapter,
)
from cip.modules.collection_orchestration.infrastructure.repository_completion import (
    insert_observations,
)
from cip.modules.data_governance.domain.retention import RetentionPolicy
from cip.modules.organizations.infrastructure.persistence import upsert_organizations
from cip.modules.procurement_history.infrastructure.projections import (
    persist_procurement_projections,
)
from cip.modules.public_footprint.infrastructure.projections import (
    persist_public_footprint_projections,
)
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_portfolio.application.execution import source_execution_allowed
from cip.modules.source_portfolio.application.service import (
    CollectionHealthUpdate,
    SourceExecutionMode,
    SourcePortfolioNotFoundError,
    SourceValueEvent,
    claim_backfill_partition,
    complete_backfill_partition,
    fail_backfill_partition,
    record_collection_failure,
    record_collection_success,
    record_source_value_event,
)
from cip.modules.source_portfolio.domain.models import SchemaState
from cip.modules.source_portfolio.infrastructure.models import BackfillPartitionRecord
from cip.modules.vulnerability_knowledge.infrastructure.projections import (
    persist_vulnerability_snapshots,
)
from cip.shared.kernel.time import require_aware_utc, utc_now
from cip.shared.persistence.session import session_scope

BACKFILL_CONTEXT_KEY = "_backfill_partition"


class BackfillWorkerStatus(StrEnum):
    IDLE = "idle"
    SUCCEEDED = "succeeded"
    NOT_MODIFIED = "not_modified"
    RETRY_SCHEDULED = "retry_scheduled"
    FAILED_TERMINAL = "failed_terminal"


@dataclass(frozen=True, slots=True)
class BackfillWorkerOutcome:
    status: BackfillWorkerStatus
    partition_id: UUID | None = None
    observations_written: int = 0
    error_code: str | None = None


def run_backfill_once(
    factory: sessionmaker[Session],
    *,
    worker_id: str,
    adapters: Mapping[tuple[str, str], CollectionAdapter],
    retention_policy: RetentionPolicy,
    clock: Callable[[], datetime] = utc_now,
) -> BackfillWorkerOutcome:
    started_at = _read_clock(clock)
    partition = _claim_partition(
        factory,
        worker_id=worker_id,
        adapters=adapters,
        now=started_at,
    )
    if partition is None:
        return BackfillWorkerOutcome(BackfillWorkerStatus.IDLE)
    adapter = adapters[(partition.source_id, partition.adapter_id)]
    retention_until = retention_policy.retention_deadline(
        adapter.data_category,
        started_at,
    )
    try:
        batch = adapter.collect(
            collection_job_id=partition.id,
            checkpoint_payload=_checkpoint_payload(partition),
            collected_at=started_at,
            retention_until=retention_until,
        )
    except AdapterExecutionError as exc:
        return _record_failure(
            factory,
            partition,
            worker_id=worker_id,
            error_code=exc.error_code,
            retryable=exc.retryable,
            now=_read_clock(clock),
        )
    except Exception:
        return _record_failure(
            factory,
            partition,
            worker_id=worker_id,
            error_code="unexpected_adapter_error",
            retryable=True,
            now=_read_clock(clock),
        )

    completed_at = _read_clock(clock)
    with session_scope(factory) as session:
        written = insert_observations(session, batch.observations)
        upsert_organizations(session, batch.procurement_organizations)
        persist_procurement_projections(
            session,
            batch.procurement_projections,
            now=completed_at,
        )
        persist_public_footprint_projections(
            session,
            batch.public_footprint_projections,
            now=completed_at,
        )
        persist_vulnerability_snapshots(
            session,
            batch.vulnerability_snapshots,
            now=completed_at,
        )
        record_collection_success(
            session,
            partition.source_id,
            CollectionHealthUpdate(
                source_record_at=_latest_source_record_at(batch.observations),
                schema_state=SchemaState.STABLE,
                quota_remaining=batch.quota_remaining,
                cost=batch.request_cost,
                observations=batch.observations,
                not_modified=batch.not_modified,
            ),
            now=completed_at,
        )
        complete_backfill_partition(
            session,
            partition.id,
            cursor=_provider_cursor(batch.checkpoint_payload),
            records_written=written,
            actor=worker_id,
            now=completed_at,
        )
        record_source_value_event(
            session,
            SourceValueEvent(
                source_id=partition.source_id,
                execution_id=partition.id,
                execution_mode=SourceExecutionMode.HISTORICAL_BACKFILL,
                observations_written=written,
                commercial_projections=0,
                identity_projections=0,
                request_cost=batch.request_cost,
                not_modified=batch.not_modified,
                occurred_at=completed_at,
            ),
        )
    status = (
        BackfillWorkerStatus.NOT_MODIFIED
        if batch.not_modified
        else BackfillWorkerStatus.SUCCEEDED
    )
    return BackfillWorkerOutcome(
        status,
        partition_id=partition.id,
        observations_written=written,
    )


def _claim_partition(
    factory: sessionmaker[Session],
    *,
    worker_id: str,
    adapters: Mapping[tuple[str, str], CollectionAdapter],
    now: datetime,
) -> BackfillPartitionRecord | None:
    seen_sources: set[str] = set()
    with session_scope(factory) as session:
        for source_id, _adapter_id in sorted(adapters):
            if source_id in seen_sources:
                continue
            seen_sources.add(source_id)
            if not source_execution_allowed(session, source_id, now=now):
                continue
            try:
                partition = claim_backfill_partition(
                    session,
                    source_id,
                    actor=worker_id,
                    now=now,
                )
            except SourcePortfolioNotFoundError:
                continue
            if partition is not None:
                return partition
    return None


def _record_failure(
    factory: sessionmaker[Session],
    partition: BackfillPartitionRecord,
    *,
    worker_id: str,
    error_code: str,
    retryable: bool,
    now: datetime,
) -> BackfillWorkerOutcome:
    with session_scope(factory) as session:
        fail_backfill_partition(
            session,
            partition.id,
            cursor=dict(partition.cursor),
            error_code=error_code,
            retryable=retryable,
            actor=worker_id,
            now=now,
        )
        record_collection_failure(
            session,
            partition.source_id,
            error_code=error_code,
            schema_drift=error_code == "source_schema_drift",
            now=now,
        )
    return BackfillWorkerOutcome(
        BackfillWorkerStatus.RETRY_SCHEDULED
        if retryable
        else BackfillWorkerStatus.FAILED_TERMINAL,
        partition_id=partition.id,
        error_code=error_code,
    )


def _checkpoint_payload(partition: BackfillPartitionRecord) -> dict[str, object]:
    payload = dict(partition.cursor)
    payload[BACKFILL_CONTEXT_KEY] = {
        "partition_id": str(partition.id),
        "lower_bound": partition.lower_bound,
        "upper_bound": partition.upper_bound,
    }
    return payload


def _provider_cursor(payload: Mapping[str, object]) -> dict[str, object]:
    cursor = dict(payload)
    cursor.pop(BACKFILL_CONTEXT_KEY, None)
    return cursor


def _latest_source_record_at(
    observations: tuple[RawObservation, ...],
) -> datetime | None:
    return max(
        (
            observation.source_updated_at
            or observation.observed_at
            or observation.published_at
            or observation.collected_at
            for observation in observations
        ),
        default=None,
    )


def _read_clock(clock: Callable[[], datetime]) -> datetime:
    return require_aware_utc(clock(), field_name="clock")

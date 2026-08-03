from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cip.modules.collection_orchestration.domain.models import JobStatus
from cip.modules.collection_orchestration.infrastructure.models import (
    CollectionCheckpointRecord,
    CollectionDeadLetterRecord,
    CollectionJobRecord,
)
from cip.shared.kernel.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class SourceCollectionMetrics:
    source_id: str
    adapter_id: str
    last_success_at: datetime | None
    last_observation_at: datetime | None
    freshness_seconds: float | None
    queue_lag_seconds: float | None
    pending_jobs: int
    running_jobs: int
    retry_jobs: int
    errors_24h: int
    dead_letters: int
    observations_written_total: int


def read_source_collection_metrics(
    session: Session,
    *,
    source_id: str,
    adapter_id: str,
    now: datetime,
) -> SourceCollectionMetrics:
    current = require_aware_utc(now, field_name="now")
    checkpoint = session.get(CollectionCheckpointRecord, (source_id, adapter_id))
    pending = _count_status(session, source_id, adapter_id, JobStatus.PENDING)
    running = _count_status(session, source_id, adapter_id, JobStatus.RUNNING)
    retry = _count_status(session, source_id, adapter_id, JobStatus.RETRY_SCHEDULED)
    oldest_active_raw = session.scalar(
        select(func.min(CollectionJobRecord.scheduled_for)).where(
            CollectionJobRecord.source_id == source_id,
            CollectionJobRecord.adapter_id == adapter_id,
            CollectionJobRecord.status.in_(
                (
                    JobStatus.PENDING.value,
                    JobStatus.RUNNING.value,
                    JobStatus.RETRY_SCHEDULED.value,
                )
            ),
        )
    )
    oldest_active = _database_utc(oldest_active_raw)
    errors_24h = int(
        session.scalar(
            select(func.count(CollectionJobRecord.id)).where(
                CollectionJobRecord.source_id == source_id,
                CollectionJobRecord.adapter_id == adapter_id,
                CollectionJobRecord.error_code.is_not(None),
                CollectionJobRecord.available_at >= current - timedelta(hours=24),
            )
        )
        or 0
    )
    dead_letters = int(
        session.scalar(
            select(func.count(CollectionDeadLetterRecord.id)).where(
                CollectionDeadLetterRecord.source_id == source_id,
                CollectionDeadLetterRecord.adapter_id == adapter_id,
            )
        )
        or 0
    )
    volume = int(
        session.scalar(
            select(func.coalesce(func.sum(CollectionJobRecord.observations_written), 0)).where(
                CollectionJobRecord.source_id == source_id,
                CollectionJobRecord.adapter_id == adapter_id,
            )
        )
        or 0
    )
    last_success = _database_utc(checkpoint.last_success_at if checkpoint else None)
    last_observation = _database_utc(
        checkpoint.last_observation_at if checkpoint else None
    )
    return SourceCollectionMetrics(
        source_id=source_id,
        adapter_id=adapter_id,
        last_success_at=last_success,
        last_observation_at=last_observation,
        freshness_seconds=(current - last_success).total_seconds() if last_success else None,
        queue_lag_seconds=(current - oldest_active).total_seconds() if oldest_active else None,
        pending_jobs=pending,
        running_jobs=running,
        retry_jobs=retry,
        errors_24h=errors_24h,
        dead_letters=dead_letters,
        observations_written_total=volume,
    )


def _count_status(
    session: Session,
    source_id: str,
    adapter_id: str,
    status: JobStatus,
) -> int:
    return int(
        session.scalar(
            select(func.count(CollectionJobRecord.id)).where(
                CollectionJobRecord.source_id == source_id,
                CollectionJobRecord.adapter_id == adapter_id,
                CollectionJobRecord.status == status.value,
            )
        )
        or 0
    )


def _database_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

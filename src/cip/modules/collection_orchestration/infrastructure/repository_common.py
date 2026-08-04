from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from cip.modules.collection_orchestration.application.ports import ClaimedJob
from cip.modules.collection_orchestration.domain.models import JobStatus
from cip.modules.collection_orchestration.infrastructure.models import CollectionJobRecord


class LeaseLostError(RuntimeError):
    """A worker attempted to update a job after losing ownership of its lease."""


def owned_running_job(
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
    lease_expires_at = optional_database_utc(record.lease_expires_at)
    if require_unexpired and (lease_expires_at is None or lease_expires_at <= now):
        raise LeaseLostError("job lease has expired")
    return record


def database_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def optional_database_utc(value: datetime | None) -> datetime | None:
    return database_utc(value) if value is not None else None

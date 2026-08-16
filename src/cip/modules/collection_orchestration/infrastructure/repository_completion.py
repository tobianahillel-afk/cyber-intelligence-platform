from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    ClaimedJob,
)
from cip.modules.collection_orchestration.domain.models import JobStatus
from cip.modules.collection_orchestration.infrastructure.models import (
    CollectionCheckpointRecord,
)
from cip.modules.collection_orchestration.infrastructure.repository_circuits import (
    reset_circuit,
)
from cip.modules.collection_orchestration.infrastructure.repository_common import (
    owned_running_job,
)
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.raw_observations.infrastructure.models import RawObservationRecord
from cip.shared.kernel.time import require_aware_utc


def complete_job(
    session: Session,
    claimed: ClaimedJob,
    batch: AdapterCollectionBatch,
    *,
    now: datetime,
) -> int:
    current = require_aware_utc(now, field_name="now")
    record = owned_running_job(session, claimed=claimed, now=current)
    written = insert_observations(session, batch.observations)
    advance_checkpoint(
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
    reset_circuit(
        session,
        source_id=record.source_id,
        adapter_id=record.adapter_id,
        now=current,
    )
    return written


def persist_partial_progress(
    session: Session,
    claimed: ClaimedJob,
    batch: AdapterCollectionBatch,
    *,
    now: datetime,
) -> int:
    """Persist completed work while keeping the job eligible for failure handling."""
    current = require_aware_utc(now, field_name="now")
    record = owned_running_job(
        session,
        claimed=claimed,
        now=current,
        require_unexpired=False,
    )
    written = insert_observations(session, batch.observations)
    advance_partial_checkpoint(
        session,
        claimed=claimed,
        payload=batch.checkpoint_payload,
        observations=batch.observations,
        now=current,
    )
    record.observations_written = written
    record.not_modified = False
    return written


def cancel_claimed_job(
    session: Session,
    claimed: ClaimedJob,
    *,
    now: datetime,
    reason: str,
) -> None:
    current = require_aware_utc(now, field_name="now")
    record = owned_running_job(session, claimed=claimed, now=current)
    normalized_reason = reason.strip()
    if not normalized_reason or len(normalized_reason) > 100:
        raise ValueError("cancellation reason must be non-empty and at most 100 characters")
    record.status = JobStatus.CANCELLED.value
    record.finished_at = current
    record.lease_owner = None
    record.lease_expires_at = None
    record.error_code = normalized_reason
    record.error_message = "collection cancelled before adapter execution"


def advance_checkpoint(
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
    last_observation_at = _last_observation_at(observations)
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
    _update_checkpoint(
        checkpoint,
        payload=payload,
        now=now,
        last_observation_at=last_observation_at,
    )
    checkpoint.last_success_at = now


def advance_partial_checkpoint(
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
    last_observation_at = _last_observation_at(observations)
    if checkpoint is None:
        session.add(
            CollectionCheckpointRecord(
                source_id=claimed.source_id,
                adapter_id=claimed.adapter_id,
                payload=dict(payload),
                version=1,
                updated_at=now,
                last_success_at=None,
                last_observation_at=last_observation_at,
            )
        )
        return
    _update_checkpoint(
        checkpoint,
        payload=payload,
        now=now,
        last_observation_at=last_observation_at,
    )


def _update_checkpoint(
    checkpoint: CollectionCheckpointRecord,
    *,
    payload: Mapping[str, object],
    now: datetime,
    last_observation_at: datetime | None,
) -> None:
    checkpoint.payload = dict(payload)
    checkpoint.version += 1
    checkpoint.updated_at = now
    if last_observation_at is not None:
        checkpoint.last_observation_at = last_observation_at


def _last_observation_at(observations: Sequence[RawObservation]) -> datetime | None:
    return max(
        (observation.collected_at for observation in observations),
        default=None,
    )


def insert_observations(
    session: Session,
    observations: Sequence[RawObservation],
) -> int:
    if not observations:
        return 0
    values = [observation_values(observation) for observation in observations]
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        postgres_statement = postgresql_insert(RawObservationRecord).values(values)
        result = session.execute(
            postgres_statement.on_conflict_do_nothing(
                constraint="uq_raw_observation_deduplication"
            )
        )
        return int(getattr(result, "rowcount", 0) or 0)
    if dialect == "sqlite":
        sqlite_statement = sqlite_insert(RawObservationRecord).values(values)
        result = session.execute(
            sqlite_statement.on_conflict_do_nothing(
                index_elements=["source_id", "source_record_key", "payload_hash_sha256"]
            )
        )
        return int(getattr(result, "rowcount", 0) or 0)
    return _insert_portable(session, observations, values)


def _insert_portable(
    session: Session,
    observations: Sequence[RawObservation],
    values: Sequence[dict[str, Any]],
) -> int:
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


def observation_values(observation: RawObservation) -> dict[str, Any]:
    return {
        "id": observation.id,
        "source_id": observation.source_id,
        "adapter_id": observation.adapter_id,
        "adapter_version": observation.adapter_version,
        "collection_job_id": observation.collection_job_id,
        "source_record_key": observation.source_record_key,
        "source_record_type": observation.source_record_type,
        "source_record_action": observation.source_record_action.value,
        "supersedes_observation_id": observation.supersedes_observation_id,
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

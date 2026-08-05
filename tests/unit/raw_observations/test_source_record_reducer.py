from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from cip.modules.raw_observations.domain.entities import (
    RawObservation,
    SourceRecordAction,
)
from cip.modules.raw_observations.domain.reducer import reduce_source_record_state
from cip.modules.source_governance.domain.models import DataCategory

NOW = datetime(2026, 8, 5, tzinfo=UTC)


def test_backfill_and_incremental_order_converge_on_correction() -> None:
    original = _observation(index=1, effective_at=NOW)
    correction = _observation(
        index=2,
        effective_at=NOW + timedelta(minutes=1),
        action=SourceRecordAction.CORRECTION,
        supersedes=original.id,
    )

    chronological = reduce_source_record_state((original, correction))
    incremental_first = reduce_source_record_state((correction, original))

    assert chronological["record-1"].id == correction.id
    assert incremental_first["record-1"].id == correction.id


def test_tombstone_and_retraction_remove_active_record() -> None:
    original = _observation(index=1, effective_at=NOW)
    correction = _observation(
        index=2,
        effective_at=NOW + timedelta(minutes=1),
        action=SourceRecordAction.CORRECTION,
        supersedes=original.id,
    )
    tombstone = _observation(
        index=3,
        effective_at=NOW + timedelta(minutes=2),
        action=SourceRecordAction.TOMBSTONE,
        supersedes=correction.id,
    )
    retraction = _observation(
        index=4,
        effective_at=NOW + timedelta(minutes=3),
        action=SourceRecordAction.RETRACTION,
        supersedes=tombstone.id,
    )

    assert reduce_source_record_state((tombstone, correction, original)) == {}
    assert reduce_source_record_state((original, correction, retraction)) == {}


def test_replay_is_idempotent() -> None:
    original = _observation(index=1, effective_at=NOW)

    state = reduce_source_record_state((original, original))

    assert tuple(state) == ("record-1",)
    assert state["record-1"].id == original.id


def _observation(
    *,
    index: int,
    effective_at: datetime,
    action: SourceRecordAction = SourceRecordAction.UPSERT,
    supersedes: UUID | None = None,
) -> RawObservation:
    return RawObservation(
        source_id="reference-synthetic",
        adapter_id="reference-synthetic-adapter",
        adapter_version="1.0.0",
        collection_job_id=uuid4(),
        source_record_type="reference_record",
        source_record_key="record-1",
        source_record_action=action,
        supersedes_observation_id=supersedes,
        source_url="https://example.invalid/records/1",
        payload_hash_sha256=f"{index:064x}"[-64:],
        data_categories=frozenset({DataCategory.PUBLIC_RESULT_METADATA}),
        collected_at=effective_at,
        source_updated_at=effective_at,
        retention_until=effective_at + timedelta(days=30),
    )

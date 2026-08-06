from __future__ import annotations

from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.threat_telemetry.domain.models import IndicatorSnapshot
from cip.modules.threat_telemetry.domain.reconciliation import (
    reconcile_indicator_snapshots,
)
from cip.modules.threat_telemetry.infrastructure.models import (
    ThreatIndicatorRecord,
    ThreatIndicatorRelationRecord,
    ThreatIndicatorSnapshotRecord,
)
from cip.modules.threat_telemetry.infrastructure.projection_hydration import (
    latest_indicator_snapshots,
)
from cip.modules.threat_telemetry.infrastructure.projection_payloads import (
    indicator_snapshot_digest,
    relation_digest,
)
from cip.shared.kernel.time import require_aware_utc


def persist_indicator_snapshots(
    session: Session,
    snapshots: tuple[IndicatorSnapshot, ...],
    *,
    now: datetime,
) -> tuple[UUID, ...]:
    if not snapshots:
        return ()
    persisted_at = require_aware_utc(now, field_name="now")
    touched: set[UUID] = set()
    for snapshot in snapshots:
        indicator = _resolve_indicator(session, snapshot, now=persisted_at)
        _insert_snapshot(session, indicator.id, snapshot, now=persisted_at)
        touched.add(indicator.id)
    for indicator_id in touched:
        _refresh_indicator(session, indicator_id, now=persisted_at)
    session.flush()
    return tuple(sorted(touched, key=str))


def _resolve_indicator(
    session: Session,
    snapshot: IndicatorSnapshot,
    *,
    now: datetime,
) -> ThreatIndicatorRecord:
    existing = session.scalar(
        select(ThreatIndicatorRecord).where(
            ThreatIndicatorRecord.indicator_key == snapshot.indicator_key
        )
    )
    if existing is not None:
        return existing
    record = ThreatIndicatorRecord(
        id=uuid5(NAMESPACE_URL, f"threat-indicator:{snapshot.indicator_key}"),
        indicator_key=snapshot.indicator_key,
        indicator_type=snapshot.indicator_type.value,
        indicator_value=snapshot.indicator_value,
        state=snapshot.state.value,
        observed_states=snapshot.state.value,
        first_seen_at=snapshot.first_seen_at,
        last_seen_at=snapshot.last_seen_at,
        expires_at=snapshot.expires_at,
        last_updated_at=snapshot.modified_at,
        source_count=1,
        independent_source_count=1 if snapshot.is_positive_detection else 0,
        active=snapshot.active,
        shared_infrastructure=snapshot.shared_infrastructure,
        historical_only=snapshot.historical_only,
        has_conflict=False,
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    session.flush()
    return record


def _insert_snapshot(
    session: Session,
    indicator_id: UUID,
    snapshot: IndicatorSnapshot,
    *,
    now: datetime,
) -> ThreatIndicatorSnapshotRecord:
    snapshot_key = indicator_snapshot_digest(snapshot)
    existing = session.scalar(
        select(ThreatIndicatorSnapshotRecord).where(
            ThreatIndicatorSnapshotRecord.snapshot_key == snapshot_key
        )
    )
    if existing is not None:
        if existing.indicator_id != indicator_id:
            raise ValueError("indicator snapshot cannot move between indicators")
        return existing
    record = ThreatIndicatorSnapshotRecord(
        id=uuid5(NAMESPACE_URL, f"threat-indicator-snapshot:{snapshot_key}"),
        indicator_id=indicator_id,
        snapshot_key=snapshot_key,
        source_id=snapshot.source_id,
        source_kind=snapshot.source_kind.value,
        source_record_key=snapshot.source_record_key,
        source_url=snapshot.source_url,
        indicator_type=snapshot.indicator_type.value,
        indicator_value=snapshot.indicator_value,
        state=snapshot.state.value,
        published_at=snapshot.published_at,
        modified_at=snapshot.modified_at,
        first_seen_at=snapshot.first_seen_at,
        last_seen_at=snapshot.last_seen_at,
        expires_at=snapshot.expires_at,
        independence_key=snapshot.independence_key or snapshot.source_id,
        sensor_scope=snapshot.sensor_scope.value,
        confidence=snapshot.confidence,
        source_precedence=snapshot.source_precedence,
        active=snapshot.active,
        shared_infrastructure=snapshot.shared_infrastructure,
        historical_only=snapshot.historical_only,
        metadata_only=snapshot.metadata_only,
        binary_payload_present=snapshot.binary_payload_present,
        direct_validation_performed=snapshot.direct_validation_performed,
        supersedes_record_key=snapshot.supersedes_record_key,
        created_at=now,
    )
    session.add(record)
    session.flush()
    _insert_relations(session, record.id, snapshot_key, snapshot)
    return record


def _insert_relations(
    session: Session,
    snapshot_id: UUID,
    snapshot_key: str,
    snapshot: IndicatorSnapshot,
) -> None:
    for relation in snapshot.relations:
        key = relation_digest(
            snapshot_key,
            relation.relation_type.value,
            relation.target_key,
        )
        session.add(
            ThreatIndicatorRelationRecord(
                id=uuid5(NAMESPACE_URL, f"threat-indicator-relation:{key}"),
                snapshot_id=snapshot_id,
                relation_key=key,
                relation_type=relation.relation_type.value,
                target_key=relation.target_key,
                confidence=relation.confidence,
            )
        )
    session.flush()


def _refresh_indicator(
    session: Session,
    indicator_id: UUID,
    *,
    now: datetime,
) -> None:
    record = session.get(ThreatIndicatorRecord, indicator_id)
    if record is None:
        raise ValueError("threat indicator disappeared during reconciliation")
    snapshots = latest_indicator_snapshots(session, indicator_id)
    reconciled = reconcile_indicator_snapshots(snapshots)[0]
    record.indicator_type = reconciled.indicator_type.value
    record.indicator_value = reconciled.indicator_value
    record.state = reconciled.state.value
    record.observed_states = ",".join(state.value for state in reconciled.observed_states)
    record.first_seen_at = reconciled.first_seen_at
    record.last_seen_at = reconciled.last_seen_at
    record.expires_at = reconciled.expires_at
    record.last_updated_at = reconciled.last_updated_at
    record.source_count = reconciled.source_count
    record.independent_source_count = reconciled.independent_source_count
    record.active = reconciled.active
    record.shared_infrastructure = reconciled.shared_infrastructure
    record.historical_only = reconciled.historical_only
    record.has_conflict = reconciled.has_conflict
    record.updated_at = now

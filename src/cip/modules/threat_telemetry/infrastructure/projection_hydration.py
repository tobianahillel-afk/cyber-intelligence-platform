from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.threat_telemetry.domain.models import (
    IndicatorSnapshot,
    IndicatorState,
    IndicatorType,
    SensorScope,
    TelemetryRelation,
    TelemetryRelationType,
    TelemetrySourceKind,
)
from cip.modules.threat_telemetry.infrastructure.models import (
    ThreatIndicatorRelationRecord,
    ThreatIndicatorSnapshotRecord,
)


def latest_indicator_snapshots(
    session: Session,
    indicator_id: UUID,
) -> tuple[IndicatorSnapshot, ...]:
    records = tuple(
        session.scalars(
            select(ThreatIndicatorSnapshotRecord)
            .where(ThreatIndicatorSnapshotRecord.indicator_id == indicator_id)
            .order_by(ThreatIndicatorSnapshotRecord.modified_at.desc())
        )
    )
    latest: dict[tuple[str, str], ThreatIndicatorSnapshotRecord] = {}
    for record in records:
        latest.setdefault((record.source_id, record.source_record_key), record)
    relations = _relations_by_snapshot(session, tuple(record.id for record in latest.values()))
    return tuple(
        _to_domain(record, relations.get(record.id, ()))
        for record in latest.values()
    )


def _relations_by_snapshot(
    session: Session,
    snapshot_ids: tuple[UUID, ...],
) -> dict[UUID, tuple[TelemetryRelation, ...]]:
    if not snapshot_ids:
        return {}
    grouped: dict[UUID, list[TelemetryRelation]] = defaultdict(list)
    records = session.scalars(
        select(ThreatIndicatorRelationRecord).where(
            ThreatIndicatorRelationRecord.snapshot_id.in_(snapshot_ids)
        )
    )
    for record in records:
        grouped[record.snapshot_id].append(
            TelemetryRelation(
                relation_type=TelemetryRelationType(record.relation_type),
                target_key=record.target_key,
                confidence=record.confidence,
            )
        )
    return {key: tuple(value) for key, value in grouped.items()}


def _to_domain(
    record: ThreatIndicatorSnapshotRecord,
    relations: tuple[TelemetryRelation, ...],
) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        source_id=record.source_id,
        source_kind=TelemetrySourceKind(record.source_kind),
        source_record_key=record.source_record_key,
        source_url=record.source_url,
        indicator_type=IndicatorType(record.indicator_type),
        indicator_value=record.indicator_value,
        state=IndicatorState(record.state),
        published_at=record.published_at,
        modified_at=record.modified_at,
        first_seen_at=record.first_seen_at,
        last_seen_at=record.last_seen_at,
        expires_at=record.expires_at,
        independence_key=record.independence_key,
        sensor_scope=SensorScope(record.sensor_scope),
        confidence=record.confidence,
        source_precedence=record.source_precedence,
        active=record.active,
        shared_infrastructure=record.shared_infrastructure,
        historical_only=record.historical_only,
        metadata_only=record.metadata_only,
        binary_payload_present=record.binary_payload_present,
        direct_validation_performed=record.direct_validation_performed,
        supersedes_record_key=record.supersedes_record_key,
        relations=relations,
    )

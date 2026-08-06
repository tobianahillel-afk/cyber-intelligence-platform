from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from cip.modules.threat_telemetry.application.view_models import (
    IndicatorDetail,
    IndicatorFilters,
    IndicatorPage,
    IndicatorRelationView,
    IndicatorSnapshotView,
    IndicatorSummary,
)
from cip.modules.threat_telemetry.infrastructure.errors import (
    ThreatIndicatorNotFoundError,
)
from cip.modules.threat_telemetry.infrastructure.models import (
    ThreatIndicatorRecord,
    ThreatIndicatorRelationRecord,
    ThreatIndicatorSnapshotRecord,
)


def list_threat_indicators(
    session: Session,
    *,
    filters: IndicatorFilters,
    limit: int,
    offset: int,
) -> IndicatorPage:
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")
    if offset < 0:
        raise ValueError("offset cannot be negative")
    statement = _apply_filters(select(ThreatIndicatorRecord), filters)
    total = session.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    )
    records = tuple(
        session.scalars(
            statement.order_by(ThreatIndicatorRecord.last_updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return IndicatorPage(
        items=tuple(_summary(record) for record in records),
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )


def get_threat_indicator_detail(
    session: Session,
    indicator_id: UUID,
) -> IndicatorDetail:
    indicator = session.get(ThreatIndicatorRecord, indicator_id)
    if indicator is None:
        raise ThreatIndicatorNotFoundError(str(indicator_id))
    snapshots = tuple(
        session.scalars(
            select(ThreatIndicatorSnapshotRecord)
            .where(ThreatIndicatorSnapshotRecord.indicator_id == indicator_id)
            .order_by(ThreatIndicatorSnapshotRecord.modified_at.desc())
        )
    )
    relations = _relations_by_snapshot(
        session,
        tuple(snapshot.id for snapshot in snapshots),
    )
    return IndicatorDetail(
        indicator=_summary(indicator),
        snapshots=tuple(
            _snapshot_view(snapshot, relations.get(snapshot.id, ()))
            for snapshot in snapshots
        ),
    )


def _apply_filters(
    statement: Select[tuple[ThreatIndicatorRecord]],
    filters: IndicatorFilters,
) -> Select[tuple[ThreatIndicatorRecord]]:
    if filters.indicator_type:
        statement = statement.where(
            ThreatIndicatorRecord.indicator_type == filters.indicator_type
        )
    if filters.state:
        statement = statement.where(ThreatIndicatorRecord.state == filters.state)
    if filters.active is not None:
        statement = statement.where(ThreatIndicatorRecord.active == filters.active)
    if filters.shared_infrastructure is not None:
        statement = statement.where(
            ThreatIndicatorRecord.shared_infrastructure
            == filters.shared_infrastructure
        )
    if filters.historical_only is not None:
        statement = statement.where(
            ThreatIndicatorRecord.historical_only == filters.historical_only
        )
    if filters.has_conflict is not None:
        statement = statement.where(
            ThreatIndicatorRecord.has_conflict == filters.has_conflict
        )
    if filters.query:
        pattern = f"%{filters.query.strip()}%"
        statement = statement.where(
            or_(
                ThreatIndicatorRecord.indicator_key.ilike(pattern),
                ThreatIndicatorRecord.indicator_value.ilike(pattern),
            )
        )
    if filters.source_kind:
        statement = statement.where(
            select(ThreatIndicatorSnapshotRecord.id)
            .where(
                ThreatIndicatorSnapshotRecord.indicator_id
                == ThreatIndicatorRecord.id,
                ThreatIndicatorSnapshotRecord.source_kind == filters.source_kind,
            )
            .exists()
        )
    if filters.sensor_scope:
        statement = statement.where(
            select(ThreatIndicatorSnapshotRecord.id)
            .where(
                ThreatIndicatorSnapshotRecord.indicator_id
                == ThreatIndicatorRecord.id,
                ThreatIndicatorSnapshotRecord.sensor_scope == filters.sensor_scope,
            )
            .exists()
        )
    return statement


def _relations_by_snapshot(
    session: Session,
    snapshot_ids: tuple[UUID, ...],
) -> dict[UUID, tuple[IndicatorRelationView, ...]]:
    if not snapshot_ids:
        return {}
    grouped: dict[UUID, list[IndicatorRelationView]] = defaultdict(list)
    records = session.scalars(
        select(ThreatIndicatorRelationRecord).where(
            ThreatIndicatorRelationRecord.snapshot_id.in_(snapshot_ids)
        )
    )
    for record in records:
        grouped[record.snapshot_id].append(
            IndicatorRelationView(
                relation_type=record.relation_type,
                target_key=record.target_key,
                confidence=record.confidence,
            )
        )
    return {key: tuple(value) for key, value in grouped.items()}


def _summary(record: ThreatIndicatorRecord) -> IndicatorSummary:
    return IndicatorSummary(
        id=record.id,
        indicator_key=record.indicator_key,
        indicator_type=record.indicator_type,
        indicator_value=record.indicator_value,
        state=record.state,
        observed_states=tuple(
            value for value in record.observed_states.split(",") if value
        ),
        first_seen_at=record.first_seen_at,
        last_seen_at=record.last_seen_at,
        expires_at=record.expires_at,
        last_updated_at=record.last_updated_at,
        source_count=record.source_count,
        independent_source_count=record.independent_source_count,
        active=record.active,
        shared_infrastructure=record.shared_infrastructure,
        historical_only=record.historical_only,
        has_conflict=record.has_conflict,
    )


def _snapshot_view(
    record: ThreatIndicatorSnapshotRecord,
    relations: tuple[IndicatorRelationView, ...],
) -> IndicatorSnapshotView:
    return IndicatorSnapshotView(
        id=record.id,
        source_id=record.source_id,
        source_kind=record.source_kind,
        source_record_key=record.source_record_key,
        source_url=record.source_url,
        state=record.state,
        published_at=record.published_at,
        modified_at=record.modified_at,
        first_seen_at=record.first_seen_at,
        last_seen_at=record.last_seen_at,
        expires_at=record.expires_at,
        independence_key=record.independence_key,
        sensor_scope=record.sensor_scope,
        confidence=record.confidence,
        source_precedence=record.source_precedence,
        active=record.active,
        shared_infrastructure=record.shared_infrastructure,
        historical_only=record.historical_only,
        metadata_only=record.metadata_only,
        supersedes_record_key=record.supersedes_record_key,
        relations=relations,
    )

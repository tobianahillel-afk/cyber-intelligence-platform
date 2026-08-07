from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from cip.modules.passive_exposure.application.view_models import (
    PassiveAssetDetail,
    PassiveAssetFilters,
    PassiveAssetPage,
    PassiveAssetSummary,
    PassiveObservationView,
    PassiveTechnologyView,
)
from cip.modules.passive_exposure.infrastructure.errors import (
    PassiveAssetNotFoundError,
)
from cip.modules.passive_exposure.infrastructure.models import (
    PassiveAssetRecord,
    PassiveObservationSnapshotRecord,
    PassiveTechnologyRecord,
)
from cip.modules.passive_exposure.infrastructure.persistence_time import (
    normalize_optional_utc,
    normalize_utc,
)
from cip.modules.passive_exposure.infrastructure.projection_payloads import (
    decode_text_values,
    decode_uuid_values,
)


def list_passive_assets(
    session: Session,
    *,
    filters: PassiveAssetFilters,
    limit: int,
    offset: int,
) -> PassiveAssetPage:
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")
    if offset < 0:
        raise ValueError("offset cannot be negative")
    statement = _apply_filters(select(PassiveAssetRecord), filters)
    total = session.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    )
    records = tuple(
        session.scalars(
            statement.order_by(PassiveAssetRecord.last_updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return PassiveAssetPage(
        items=tuple(_summary(record) for record in records),
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )


def get_passive_asset_detail(
    session: Session,
    asset_id: UUID,
) -> PassiveAssetDetail:
    asset = session.get(PassiveAssetRecord, asset_id)
    if asset is None:
        raise PassiveAssetNotFoundError(str(asset_id))
    snapshots = tuple(
        session.scalars(
            select(PassiveObservationSnapshotRecord)
            .where(PassiveObservationSnapshotRecord.asset_id == asset_id)
            .order_by(PassiveObservationSnapshotRecord.modified_at.desc())
        )
    )
    technologies = _technologies_by_snapshot(
        session,
        tuple(snapshot.id for snapshot in snapshots),
    )
    return PassiveAssetDetail(
        asset=_summary(asset),
        observations=tuple(
            _observation_view(snapshot, technologies.get(snapshot.id))
            for snapshot in snapshots
        ),
    )


def _apply_filters(
    statement: Select[tuple[PassiveAssetRecord]],
    filters: PassiveAssetFilters,
) -> Select[tuple[PassiveAssetRecord]]:
    if filters.asset_kind:
        statement = statement.where(PassiveAssetRecord.asset_kind == filters.asset_kind)
    if filters.state:
        statement = statement.where(PassiveAssetRecord.state == filters.state)
    if filters.organization_link_status:
        statement = statement.where(
            PassiveAssetRecord.organization_link_status
            == filters.organization_link_status
        )
    if filters.active is not None:
        statement = statement.where(PassiveAssetRecord.active == filters.active)
    if filters.historical_only is not None:
        statement = statement.where(
            PassiveAssetRecord.historical_only == filters.historical_only
        )
    if filters.has_conflict is not None:
        statement = statement.where(
            PassiveAssetRecord.has_conflict == filters.has_conflict
        )
    if filters.attribution_risk:
        pattern = f'%"{filters.attribution_risk}"%'
        statement = statement.where(PassiveAssetRecord.attribution_risks.like(pattern))
    if filters.organization_id:
        identifier = str(filters.organization_id)
        statement = statement.where(
            or_(
                PassiveAssetRecord.exact_organization_id == filters.organization_id,
                PassiveAssetRecord.candidate_organization_ids.like(f'%"{identifier}"%'),
            )
        )
    if filters.query:
        pattern = f"%{filters.query.strip()}%"
        statement = statement.where(
            or_(
                PassiveAssetRecord.asset_key.ilike(pattern),
                PassiveAssetRecord.asset_value.ilike(pattern),
            )
        )
    return statement


def _technologies_by_snapshot(
    session: Session,
    snapshot_ids: tuple[UUID, ...],
) -> dict[UUID, PassiveTechnologyView]:
    if not snapshot_ids:
        return {}
    records = session.scalars(
        select(PassiveTechnologyRecord).where(
            PassiveTechnologyRecord.snapshot_id.in_(snapshot_ids)
        )
    )
    return {
        record.snapshot_id: PassiveTechnologyView(
            evidence_level=record.evidence_level,
            product_name=record.product_name,
            product_version=record.product_version,
            component_name=record.component_name,
        )
        for record in records
    }


def _summary(record: PassiveAssetRecord) -> PassiveAssetSummary:
    return PassiveAssetSummary(
        id=record.id,
        asset_key=record.asset_key,
        asset_kind=record.asset_kind,
        asset_value=record.asset_value,
        state=record.state,
        observed_states=tuple(value for value in record.observed_states.split(",") if value),
        first_seen_at=normalize_utc(record.first_seen_at),
        last_seen_at=normalize_utc(record.last_seen_at),
        expires_at=normalize_optional_utc(record.expires_at),
        last_updated_at=normalize_utc(record.last_updated_at),
        source_count=record.source_count,
        independent_source_count=record.independent_source_count,
        active=record.active,
        historical_only=record.historical_only,
        has_conflict=record.has_conflict,
        organization_link_status=record.organization_link_status,
        exact_organization_id=record.exact_organization_id,
        candidate_organization_ids=decode_uuid_values(
            record.candidate_organization_ids
        ),
        organization_link_reasons=decode_text_values(
            record.organization_link_reasons
        ),
        attribution_risks=decode_text_values(record.attribution_risks),
    )


def _observation_view(
    record: PassiveObservationSnapshotRecord,
    technology: PassiveTechnologyView | None,
) -> PassiveObservationView:
    return PassiveObservationView(
        id=record.id,
        source_id=record.source_id,
        source_record_key=record.source_record_key,
        source_url=record.source_url,
        observation_kind=record.observation_kind,
        state=record.state,
        observed_at=normalize_utc(record.observed_at),
        published_at=normalize_utc(record.published_at),
        modified_at=normalize_utc(record.modified_at),
        expires_at=normalize_optional_utc(record.expires_at),
        independence_key=record.independence_key,
        confidence=record.confidence,
        organization_id=record.organization_id,
        organization_link_status=record.organization_link_status,
        organization_link_method=record.organization_link_method,
        organization_link_confidence=record.organization_link_confidence,
        organization_link_reasons=decode_text_values(
            record.organization_link_reasons
        ),
        attribution_risks=decode_text_values(record.attribution_risks),
        port=record.port,
        protocol=record.protocol,
        active=record.active,
        historical_only=record.historical_only,
        metadata_only=record.metadata_only,
        passive_only=record.passive_only,
        supersedes_record_key=record.supersedes_record_key,
        technology=technology,
    )

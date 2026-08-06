from __future__ import annotations

from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.orm import Session

from cip.modules.incident_intelligence.application.view_models import (
    IncidentClaimView,
    IncidentDetail,
    IncidentFilters,
    IncidentPage,
    IncidentSummary,
)
from cip.modules.incident_intelligence.infrastructure.errors import (
    IncidentNotFoundError,
)
from cip.modules.incident_intelligence.infrastructure.models import (
    IncidentClaimSnapshotRecord,
    IncidentRecord,
)
from cip.modules.organizations.infrastructure.persistence_time import coerce_utc


def list_incidents(
    session: Session,
    *,
    filters: IncidentFilters,
    limit: int,
    offset: int,
) -> IncidentPage:
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")
    if offset < 0:
        raise ValueError("offset cannot be negative")
    statement = _apply_filters(select(IncidentRecord), filters)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = tuple(
        session.scalars(
            statement.order_by(
                IncidentRecord.last_updated_at.desc(),
                IncidentRecord.incident_key,
            )
            .limit(limit)
            .offset(offset)
        )
    )
    return IncidentPage(
        items=tuple(_summary(row) for row in rows),
        total=total,
        limit=limit,
        offset=offset,
    )


def get_incident_detail(session: Session, incident_key: str) -> IncidentDetail:
    record = session.scalar(
        select(IncidentRecord).where(IncidentRecord.incident_key == incident_key)
    )
    if record is None:
        raise IncidentNotFoundError(incident_key)
    claims = tuple(
        _claim_view(row)
        for row in session.scalars(
            select(IncidentClaimSnapshotRecord)
            .where(IncidentClaimSnapshotRecord.incident_id == record.id)
            .order_by(IncidentClaimSnapshotRecord.modified_at.desc())
        )
    )
    return IncidentDetail(
        incident=_summary(record),
        claimed_organization_names=tuple(
            sorted(
                {
                    claim.claimed_organization_name
                    for claim in claims
                    if claim.claimed_organization_name is not None
                }
            )
        ),
        claims=claims,
    )


def _apply_filters(
    statement: Select[tuple[IncidentRecord]],
    filters: IncidentFilters,
) -> Select[tuple[IncidentRecord]]:
    if filters.status:
        statement = statement.where(IncidentRecord.status == filters.status)
    if filters.incident_type:
        statement = statement.where(
            IncidentRecord.incident_type == filters.incident_type
        )
    if filters.organization_link_status:
        statement = statement.where(
            IncidentRecord.organization_link_status
            == filters.organization_link_status
        )
    if filters.officially_confirmed is not None:
        statement = statement.where(
            IncidentRecord.officially_confirmed
            == filters.officially_confirmed
        )
    if filters.historical_only is not None:
        statement = statement.where(
            IncidentRecord.historical_only == filters.historical_only
        )
    if filters.query:
        pattern = f"%{filters.query.strip()}%"
        statement = statement.where(
            or_(
                IncidentRecord.incident_key.ilike(pattern),
                IncidentRecord.title.ilike(pattern),
                IncidentRecord.summary.ilike(pattern),
            )
        )
    if filters.claim_type or filters.source_kind:
        predicates = [
            IncidentClaimSnapshotRecord.incident_id == IncidentRecord.id
        ]
        if filters.claim_type:
            predicates.append(
                IncidentClaimSnapshotRecord.claim_type == filters.claim_type
            )
        if filters.source_kind:
            predicates.append(
                IncidentClaimSnapshotRecord.source_kind == filters.source_kind
            )
        statement = statement.where(
            exists(select(IncidentClaimSnapshotRecord.id).where(*predicates))
        )
    return statement


def _summary(record: IncidentRecord) -> IncidentSummary:
    return IncidentSummary(
        id=record.id,
        incident_key=record.incident_key,
        incident_type=record.incident_type,
        title=record.title,
        summary=record.summary,
        status=record.status,
        organization_id=record.organization_id,
        organization_link_status=record.organization_link_status,
        occurrence_start_at=(
            coerce_utc(record.occurrence_start_at)
            if record.occurrence_start_at
            else None
        ),
        occurrence_end_at=(
            coerce_utc(record.occurrence_end_at)
            if record.occurrence_end_at
            else None
        ),
        discovered_at=(
            coerce_utc(record.discovered_at)
            if record.discovered_at
            else None
        ),
        first_published_at=coerce_utc(record.first_published_at),
        confirmed_at=(
            coerce_utc(record.confirmed_at)
            if record.confirmed_at
            else None
        ),
        last_updated_at=coerce_utc(record.last_updated_at),
        claim_count=record.claim_count,
        independent_source_count=record.independent_source_count,
        officially_confirmed=record.officially_confirmed,
        has_denial=record.has_denial,
        has_retraction=record.has_retraction,
        historical_only=record.historical_only,
    )


def _claim_view(record: IncidentClaimSnapshotRecord) -> IncidentClaimView:
    return IncidentClaimView(
        id=record.id,
        source_id=record.source_id,
        source_kind=record.source_kind,
        source_record_key=record.source_record_key,
        source_url=record.source_url,
        claim_type=record.claim_type,
        incident_type=record.incident_type,
        title=record.title,
        summary=record.summary,
        claimed_organization_name=record.claimed_organization_name,
        organization_id=record.organization_id,
        organization_link_status=record.organization_link_status,
        published_at=coerce_utc(record.published_at),
        modified_at=coerce_utc(record.modified_at),
        occurrence_start_at=(
            coerce_utc(record.occurrence_start_at)
            if record.occurrence_start_at
            else None
        ),
        occurrence_end_at=(
            coerce_utc(record.occurrence_end_at)
            if record.occurrence_end_at
            else None
        ),
        discovered_at=(
            coerce_utc(record.discovered_at)
            if record.discovered_at
            else None
        ),
        confirmed_at=(
            coerce_utc(record.confirmed_at)
            if record.confirmed_at
            else None
        ),
        independence_key=record.independence_key,
        confidence=record.confidence,
        active=record.active,
        historical_only=record.historical_only,
        metadata_only=record.metadata_only,
        supersedes_record_key=record.supersedes_record_key,
    )

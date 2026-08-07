from __future__ import annotations

from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.orm import Session

from cip.modules.corporate_changes.application.view_models import (
    ChangeClaimView,
    ChangeDetail,
    ChangeFilters,
    ChangePage,
    ChangeServiceMappingView,
    ChangeSummary,
)
from cip.modules.corporate_changes.infrastructure.errors import (
    CorporateChangeNotFoundError,
)
from cip.modules.corporate_changes.infrastructure.models import (
    CorporateChangeClaimSnapshotRecord,
    CorporateChangeEventRecord,
    CorporateChangeServiceMappingRecord,
)
from cip.modules.organizations.infrastructure.persistence_time import coerce_utc


def list_change_events(
    session: Session,
    *,
    filters: ChangeFilters,
    limit: int,
    offset: int,
) -> ChangePage:
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")
    if offset < 0:
        raise ValueError("offset cannot be negative")
    statement = _apply_filters(select(CorporateChangeEventRecord), filters)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = tuple(
        session.scalars(
            statement.order_by(
                CorporateChangeEventRecord.last_updated_at.desc(),
                CorporateChangeEventRecord.event_key,
            )
            .limit(limit)
            .offset(offset)
        )
    )
    return ChangePage(
        items=tuple(_summary(row) for row in rows),
        total=total,
        limit=limit,
        offset=offset,
    )


def get_change_detail(session: Session, event_key: str) -> ChangeDetail:
    record = session.scalar(
        select(CorporateChangeEventRecord).where(
            CorporateChangeEventRecord.event_key == event_key
        )
    )
    if record is None:
        raise CorporateChangeNotFoundError(event_key)
    claims = tuple(
        _claim_view(row)
        for row in session.scalars(
            select(CorporateChangeClaimSnapshotRecord)
            .where(CorporateChangeClaimSnapshotRecord.event_id == record.id)
            .order_by(CorporateChangeClaimSnapshotRecord.modified_at.desc())
        )
    )
    mappings = tuple(
        _mapping_view(row)
        for row in session.scalars(
            select(CorporateChangeServiceMappingRecord)
            .where(CorporateChangeServiceMappingRecord.event_id == record.id)
            .order_by(CorporateChangeServiceMappingRecord.service_family)
        )
    )
    return ChangeDetail(
        event=_summary(record),
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
        service_mappings=mappings,
    )


def _apply_filters(
    statement: Select[tuple[CorporateChangeEventRecord]],
    filters: ChangeFilters,
) -> Select[tuple[CorporateChangeEventRecord]]:
    if filters.status:
        statement = statement.where(CorporateChangeEventRecord.status == filters.status)
    if filters.event_type:
        statement = statement.where(
            CorporateChangeEventRecord.event_type == filters.event_type
        )
    if filters.organization_link_status:
        statement = statement.where(
            CorporateChangeEventRecord.organization_link_status
            == filters.organization_link_status
        )
    if filters.organization_id is not None:
        statement = statement.where(
            CorporateChangeEventRecord.organization_id == filters.organization_id
        )
    if filters.officially_confirmed is not None:
        statement = statement.where(
            CorporateChangeEventRecord.officially_confirmed
            == filters.officially_confirmed
        )
    if filters.historical_only is not None:
        statement = statement.where(
            CorporateChangeEventRecord.historical_only == filters.historical_only
        )
    if filters.query:
        pattern = f"%{filters.query.strip()}%"
        statement = statement.where(
            or_(
                CorporateChangeEventRecord.event_key.ilike(pattern),
                CorporateChangeEventRecord.title.ilike(pattern),
                CorporateChangeEventRecord.excerpt.ilike(pattern),
            )
        )
    if filters.claim_type or filters.source_kind:
        statement = _filter_by_claim(statement, filters)
    return statement


def _filter_by_claim(
    statement: Select[tuple[CorporateChangeEventRecord]],
    filters: ChangeFilters,
) -> Select[tuple[CorporateChangeEventRecord]]:
    predicates = [
        CorporateChangeClaimSnapshotRecord.event_id == CorporateChangeEventRecord.id
    ]
    if filters.claim_type:
        predicates.append(
            CorporateChangeClaimSnapshotRecord.claim_type == filters.claim_type
        )
    if filters.source_kind:
        predicates.append(
            CorporateChangeClaimSnapshotRecord.source_kind == filters.source_kind
        )
    return statement.where(
        exists(select(CorporateChangeClaimSnapshotRecord.id).where(*predicates))
    )


def _summary(record: CorporateChangeEventRecord) -> ChangeSummary:
    return ChangeSummary(
        id=record.id,
        event_key=record.event_key,
        event_type=record.event_type,
        title=record.title,
        excerpt=record.excerpt,
        status=record.status,
        organization_id=record.organization_id,
        organization_link_status=record.organization_link_status,
        event_at=coerce_utc(record.event_at) if record.event_at else None,
        first_published_at=coerce_utc(record.first_published_at),
        last_updated_at=coerce_utc(record.last_updated_at),
        claim_count=record.claim_count,
        independent_source_count=record.independent_source_count,
        officially_confirmed=record.officially_confirmed,
        has_dispute=record.has_dispute,
        has_correction=record.has_correction,
        has_retraction=record.has_retraction,
        historical_only=record.historical_only,
    )


def _claim_view(record: CorporateChangeClaimSnapshotRecord) -> ChangeClaimView:
    return ChangeClaimView(
        id=record.id,
        source_id=record.source_id,
        source_kind=record.source_kind,
        source_record_key=record.source_record_key,
        article_id=record.article_id,
        source_url=record.source_url,
        claim_type=record.claim_type,
        title=record.title,
        excerpt=record.excerpt,
        claimed_organization_name=record.claimed_organization_name,
        organization_id=record.organization_id,
        organization_link_status=record.organization_link_status,
        published_at=coerce_utc(record.published_at),
        modified_at=coerce_utc(record.modified_at),
        event_at=coerce_utc(record.event_at) if record.event_at else None,
        expires_at=coerce_utc(record.expires_at) if record.expires_at else None,
        independence_key=record.independence_key,
        syndication_group_key=record.syndication_group_key,
        confidence=record.confidence,
        active=record.active,
        historical_only=record.historical_only,
        supersedes_record_key=record.supersedes_record_key,
    )


def _mapping_view(
    record: CorporateChangeServiceMappingRecord,
) -> ChangeServiceMappingView:
    return ChangeServiceMappingView(
        id=record.id,
        service_family=record.service_family,
        rationale=record.rationale,
        confidence=record.confidence,
        created_at=coerce_utc(record.created_at),
    )

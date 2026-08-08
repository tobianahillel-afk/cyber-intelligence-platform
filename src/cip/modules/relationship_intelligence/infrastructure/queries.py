from __future__ import annotations

from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.orm import Session

from cip.modules.organizations.infrastructure.persistence_time import coerce_utc
from cip.modules.relationship_intelligence.application.view_models import (
    RelationshipContextView,
    RelationshipDetail,
    RelationshipEvidenceView,
    RelationshipFilters,
    RelationshipPage,
    RelationshipSummary,
)
from cip.modules.relationship_intelligence.infrastructure.errors import (
    RelationshipNotFoundError,
)
from cip.modules.relationship_intelligence.infrastructure.models import (
    BusinessRelationshipRecord,
    RelationshipContextRecord,
    RelationshipEvidenceSnapshotRecord,
)


def list_relationships(
    session: Session,
    *,
    filters: RelationshipFilters,
    limit: int,
    offset: int,
) -> RelationshipPage:
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")
    if offset < 0:
        raise ValueError("offset cannot be negative")
    statement = _apply_filters(select(BusinessRelationshipRecord), filters)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = tuple(
        session.scalars(
            statement.order_by(
                BusinessRelationshipRecord.last_updated_at.desc(),
                BusinessRelationshipRecord.relationship_key,
            )
            .limit(limit)
            .offset(offset)
        )
    )
    return RelationshipPage(
        items=tuple(_summary(row) for row in rows),
        total=total,
        limit=limit,
        offset=offset,
    )


def get_relationship_detail(
    session: Session,
    relationship_key: str,
) -> RelationshipDetail:
    record = session.scalar(
        select(BusinessRelationshipRecord).where(
            BusinessRelationshipRecord.relationship_key == relationship_key
        )
    )
    if record is None:
        raise RelationshipNotFoundError(relationship_key)
    evidence = tuple(
        _evidence_view(row)
        for row in session.scalars(
            select(RelationshipEvidenceSnapshotRecord)
            .where(RelationshipEvidenceSnapshotRecord.relationship_id == record.id)
            .order_by(RelationshipEvidenceSnapshotRecord.modified_at.desc())
        )
    )
    contexts = tuple(
        _context_view(row)
        for row in session.scalars(
            select(RelationshipContextRecord)
            .where(RelationshipContextRecord.relationship_id == record.id)
            .order_by(
                RelationshipContextRecord.context_type,
                RelationshipContextRecord.value,
            )
        )
    )
    return RelationshipDetail(
        relationship=_summary(record),
        claimed_source_organization_names=_claimed_names(evidence, source=True),
        claimed_target_organization_names=_claimed_names(evidence, source=False),
        evidence=evidence,
        contexts=contexts,
    )


def _apply_filters(
    statement: Select[tuple[BusinessRelationshipRecord]],
    filters: RelationshipFilters,
) -> Select[tuple[BusinessRelationshipRecord]]:
    if filters.status:
        statement = statement.where(BusinessRelationshipRecord.status == filters.status)
    if filters.role:
        statement = statement.where(BusinessRelationshipRecord.role == filters.role)
    if filters.source_link_status:
        statement = statement.where(
            BusinessRelationshipRecord.source_link_status == filters.source_link_status
        )
    if filters.target_link_status:
        statement = statement.where(
            BusinessRelationshipRecord.target_link_status == filters.target_link_status
        )
    if filters.organization_id is not None:
        statement = statement.where(
            or_(
                BusinessRelationshipRecord.source_organization_id == filters.organization_id,
                BusinessRelationshipRecord.target_organization_id == filters.organization_id,
            )
        )
    if filters.contract_backed_current is not None:
        statement = statement.where(
            BusinessRelationshipRecord.contract_backed_current
            == filters.contract_backed_current
        )
    if filters.historical_only is not None:
        statement = statement.where(
            BusinessRelationshipRecord.historical_only == filters.historical_only
        )
    if filters.query:
        pattern = f"%{filters.query.strip()}%"
        statement = statement.where(
            or_(
                BusinessRelationshipRecord.relationship_key.ilike(pattern),
                BusinessRelationshipRecord.source_name.ilike(pattern),
                BusinessRelationshipRecord.target_name.ilike(pattern),
            )
        )
    if filters.evidence_class or filters.source_kind:
        statement = _filter_by_evidence(statement, filters)
    return statement


def _filter_by_evidence(
    statement: Select[tuple[BusinessRelationshipRecord]],
    filters: RelationshipFilters,
) -> Select[tuple[BusinessRelationshipRecord]]:
    predicates = [
        RelationshipEvidenceSnapshotRecord.relationship_id == BusinessRelationshipRecord.id
    ]
    if filters.evidence_class:
        predicates.append(
            RelationshipEvidenceSnapshotRecord.evidence_class == filters.evidence_class
        )
    if filters.source_kind:
        predicates.append(
            RelationshipEvidenceSnapshotRecord.source_kind == filters.source_kind
        )
    return statement.where(
        exists(select(RelationshipEvidenceSnapshotRecord.id).where(*predicates))
    )


def _summary(record: BusinessRelationshipRecord) -> RelationshipSummary:
    return RelationshipSummary(
        id=record.id,
        relationship_key=record.relationship_key,
        role=record.role,
        status=record.status,
        source_organization_id=record.source_organization_id,
        target_organization_id=record.target_organization_id,
        source_link_status=record.source_link_status,
        target_link_status=record.target_link_status,
        source_name=record.source_name,
        target_name=record.target_name,
        valid_from=coerce_utc(record.valid_from) if record.valid_from else None,
        valid_until=coerce_utc(record.valid_until) if record.valid_until else None,
        first_published_at=coerce_utc(record.first_published_at),
        last_updated_at=coerce_utc(record.last_updated_at),
        last_observed_at=coerce_utc(record.last_observed_at),
        evidence_count=record.evidence_count,
        independent_source_count=record.independent_source_count,
        strongest_evidence_class=record.strongest_evidence_class,
        confidence=record.confidence,
        has_contract_evidence=record.has_contract_evidence,
        contract_backed_current=record.contract_backed_current,
        next_renewal_at=(
            coerce_utc(record.next_renewal_at) if record.next_renewal_at else None
        ),
        has_role_conflict=record.has_role_conflict,
        has_dispute=record.has_dispute,
        has_correction=record.has_correction,
        has_retraction=record.has_retraction,
        historical_only=record.historical_only,
    )


def _evidence_view(
    record: RelationshipEvidenceSnapshotRecord,
) -> RelationshipEvidenceView:
    return RelationshipEvidenceView(
        id=record.id,
        source_id=record.source_id,
        source_kind=record.source_kind,
        source_record_key=record.source_record_key,
        source_url=record.source_url,
        claim_type=record.claim_type,
        role=record.role,
        evidence_class=record.evidence_class,
        title=record.title,
        excerpt=record.excerpt,
        claimed_source_organization_name=record.claimed_source_organization_name,
        claimed_target_organization_name=record.claimed_target_organization_name,
        source_organization_id=record.source_organization_id,
        target_organization_id=record.target_organization_id,
        source_link_status=record.source_link_status,
        target_link_status=record.target_link_status,
        published_at=coerce_utc(record.published_at),
        modified_at=coerce_utc(record.modified_at),
        observed_at=coerce_utc(record.observed_at),
        valid_from=coerce_utc(record.valid_from) if record.valid_from else None,
        valid_until=coerce_utc(record.valid_until) if record.valid_until else None,
        expires_at=coerce_utc(record.expires_at) if record.expires_at else None,
        contract_reference=record.contract_reference,
        product_context=record.product_context,
        service_context=record.service_context,
        renewal_at=coerce_utc(record.renewal_at) if record.renewal_at else None,
        independence_key=record.independence_key,
        confidence=record.confidence,
        active=record.active,
        historical_only=record.historical_only,
        supersedes_record_key=record.supersedes_record_key,
    )


def _context_view(record: RelationshipContextRecord) -> RelationshipContextView:
    return RelationshipContextView(
        id=record.id,
        context_type=record.context_type,
        value=record.value,
        reference=record.reference,
        confidence=record.confidence,
        created_at=coerce_utc(record.created_at),
    )


def _claimed_names(
    evidence: tuple[RelationshipEvidenceView, ...],
    *,
    source: bool,
) -> tuple[str, ...]:
    values = {
        item.claimed_source_organization_name
        if source
        else item.claimed_target_organization_name
        for item in evidence
    }
    return tuple(sorted(value for value in values if value is not None))

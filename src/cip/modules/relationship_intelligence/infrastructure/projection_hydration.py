from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.organizations.infrastructure.persistence_time import coerce_utc
from cip.modules.relationship_intelligence.domain.models import (
    RelationshipClaimType,
    RelationshipEvidenceClass,
    RelationshipEvidenceSnapshot,
    RelationshipOrganizationLinkStatus,
    RelationshipRole,
    RelationshipSourceKind,
)
from cip.modules.relationship_intelligence.infrastructure.models import (
    RelationshipEvidenceSnapshotRecord,
)


def latest_relationship_evidence(
    session: Session,
    relationship_id: UUID,
) -> tuple[RelationshipEvidenceSnapshot, ...]:
    rows = list(
        session.scalars(
            select(RelationshipEvidenceSnapshotRecord)
            .where(RelationshipEvidenceSnapshotRecord.relationship_id == relationship_id)
            .order_by(
                RelationshipEvidenceSnapshotRecord.source_id,
                RelationshipEvidenceSnapshotRecord.source_record_key,
                RelationshipEvidenceSnapshotRecord.modified_at.desc(),
            )
        )
    )
    latest: dict[tuple[str, str], RelationshipEvidenceSnapshotRecord] = {}
    for row in rows:
        latest.setdefault((row.source_id, row.source_record_key), row)
    return tuple(_hydrate(row) for row in latest.values())


def all_relationship_evidence(
    session: Session,
    relationship_id: UUID,
) -> tuple[RelationshipEvidenceSnapshot, ...]:
    return tuple(
        _hydrate(row)
        for row in session.scalars(
            select(RelationshipEvidenceSnapshotRecord)
            .where(RelationshipEvidenceSnapshotRecord.relationship_id == relationship_id)
            .order_by(RelationshipEvidenceSnapshotRecord.modified_at.desc())
        )
    )


def _hydrate(row: RelationshipEvidenceSnapshotRecord) -> RelationshipEvidenceSnapshot:
    return RelationshipEvidenceSnapshot(
        source_id=row.source_id,
        source_kind=RelationshipSourceKind(row.source_kind),
        source_record_key=row.source_record_key,
        source_url=row.source_url,
        relationship_key=row.relationship_key,
        claim_type=RelationshipClaimType(row.claim_type),
        role=RelationshipRole(row.role),
        evidence_class=RelationshipEvidenceClass(row.evidence_class),
        title=row.title,
        excerpt=row.excerpt,
        claimed_source_organization_name=row.claimed_source_organization_name,
        claimed_target_organization_name=row.claimed_target_organization_name,
        source_organization_id=row.source_organization_id,
        target_organization_id=row.target_organization_id,
        source_link_status=RelationshipOrganizationLinkStatus(row.source_link_status),
        target_link_status=RelationshipOrganizationLinkStatus(row.target_link_status),
        published_at=coerce_utc(row.published_at),
        modified_at=coerce_utc(row.modified_at),
        observed_at=coerce_utc(row.observed_at),
        valid_from=coerce_utc(row.valid_from) if row.valid_from else None,
        valid_until=coerce_utc(row.valid_until) if row.valid_until else None,
        expires_at=coerce_utc(row.expires_at) if row.expires_at else None,
        contract_reference=row.contract_reference,
        product_context=row.product_context,
        service_context=row.service_context,
        renewal_at=coerce_utc(row.renewal_at) if row.renewal_at else None,
        independence_key=row.independence_key,
        confidence=row.confidence,
        active=row.active,
        historical_only=row.historical_only,
        metadata_only=row.metadata_only,
        supersedes_record_key=row.supersedes_record_key,
    )

from __future__ import annotations

from uuid import UUID

from cip.adapters.sources.relationship_catalogs.schemas import PublicRelationshipRecord
from cip.modules.relationship_intelligence.application.bundles import (
    RelationshipProjectionBundle,
)
from cip.modules.relationship_intelligence.domain.models import (
    RelationshipClaimType,
    RelationshipContext,
    RelationshipEvidenceClass,
    RelationshipEvidenceSnapshot,
    RelationshipOrganizationLinkStatus,
    RelationshipRole,
    RelationshipSourceKind,
)


def map_public_relationship_record(
    source_id: str,
    record: PublicRelationshipRecord,
) -> RelationshipProjectionBundle:
    source_organization_id = _organization_id(
        record.source_organization.exact_organization_id
    )
    target_organization_id = _organization_id(
        record.target_organization.exact_organization_id
    )
    snapshot = RelationshipEvidenceSnapshot(
        source_id=source_id,
        source_kind=RelationshipSourceKind(record.source_kind.value),
        source_record_key=record.record_id,
        source_url=record.source_url,
        relationship_key=record.relationship_key,
        claim_type=RelationshipClaimType(record.claim_kind.value),
        role=RelationshipRole(record.role.value),
        evidence_class=RelationshipEvidenceClass(record.evidence_class.value),
        title=record.title,
        excerpt=record.excerpt,
        claimed_source_organization_name=record.source_organization.claimed_name,
        claimed_target_organization_name=record.target_organization.claimed_name,
        source_organization_id=source_organization_id,
        target_organization_id=target_organization_id,
        source_link_status=_link_status(source_organization_id),
        target_link_status=_link_status(target_organization_id),
        published_at=record.published_at,
        modified_at=record.modified_at,
        observed_at=record.observed_at,
        valid_from=record.valid_from,
        valid_until=record.valid_until,
        expires_at=record.expires_at,
        product_context=record.product_context,
        service_context=record.service_context,
        independence_key=record.independence_key or source_id,
        confidence=record.confidence,
        active=True,
        historical_only=record.historical_only,
        supersedes_record_key=record.supersedes_record_id,
    )
    return RelationshipProjectionBundle(
        evidence=(snapshot,),
        contexts=_contexts(snapshot, record),
    )


def _contexts(
    snapshot: RelationshipEvidenceSnapshot,
    record: PublicRelationshipRecord,
) -> tuple[RelationshipContext, ...]:
    contexts: list[RelationshipContext] = []
    if record.product_context:
        contexts.append(
            RelationshipContext(
                relationship_key=snapshot.relationship_key,
                context_type="product",
                value=record.product_context,
                reference=record.source_url,
                confidence=record.confidence,
            )
        )
    if record.service_context:
        contexts.append(
            RelationshipContext(
                relationship_key=snapshot.relationship_key,
                context_type="service",
                value=record.service_context,
                reference=record.source_url,
                confidence=record.confidence,
            )
        )
    return tuple(contexts)


def _organization_id(value: str | None) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValueError("exact_organization_id must be a UUID") from exc


def _link_status(
    organization_id: UUID | None,
) -> RelationshipOrganizationLinkStatus:
    if organization_id is not None:
        return RelationshipOrganizationLinkStatus.EXACT
    return RelationshipOrganizationLinkStatus.CANDIDATE

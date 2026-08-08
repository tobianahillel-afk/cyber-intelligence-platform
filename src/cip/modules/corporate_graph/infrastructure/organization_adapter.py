from __future__ import annotations

from datetime import UTC, date, datetime, time
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.corporate_graph.application.batches import GraphProjectionBatch
from cip.modules.corporate_graph.domain.models import (
    GraphClaimType,
    GraphEdgeSnapshot,
    GraphEdgeType,
    GraphNodeSnapshot,
    GraphNodeType,
    GraphReviewState,
)
from cip.modules.organizations.infrastructure.identity_models import (
    OrganizationIdentityRecord,
    OrganizationRelationshipRecord,
)
from cip.modules.organizations.infrastructure.models import OrganizationRecord

_IDENTITY_NODE_TYPES = {
    "legal_unit": GraphNodeType.ORGANIZATION,
    "establishment": GraphNodeType.ESTABLISHMENT,
    "brand": GraphNodeType.BRAND,
    "group": GraphNodeType.GROUP,
}
_RELATIONSHIP_EDGE_TYPES = {
    "establishment_of": GraphEdgeType.ESTABLISHMENT_OF,
    "headquarters_of": GraphEdgeType.ESTABLISHMENT_OF,
    "direct_parent": GraphEdgeType.PARENT_OF,
    "ultimate_parent": GraphEdgeType.PARENT_OF,
    "subsidiary": GraphEdgeType.SUBSIDIARY_OF,
    "brand_of": GraphEdgeType.BRAND_OF,
}


def load_organization_graph(session: Session) -> GraphProjectionBatch:
    organizations = tuple(session.scalars(select(OrganizationRecord)).all())
    identities = tuple(session.scalars(select(OrganizationIdentityRecord)).all())
    relationships = tuple(session.scalars(select(OrganizationRelationshipRecord)).all())
    nodes: list[GraphNodeSnapshot] = []
    edges: list[GraphEdgeSnapshot] = []
    for organization in organizations:
        nodes.append(_organization_node(organization))
        domain = _website_domain(organization.website_url)
        if domain is not None:
            nodes.append(_domain_node(organization, domain))
            edges.append(_organization_domain_edge(organization, domain))
    for identity in identities:
        nodes.append(_identity_node(identity))
        if identity.organization_id is not None:
            edges.append(_identity_binding_edge(identity))
    for relationship in relationships:
        edge = _structural_edge(relationship)
        if edge is not None:
            edges.append(edge)
    return GraphProjectionBatch(nodes=tuple(nodes), edges=tuple(edges))


def _organization_node(record: OrganizationRecord) -> GraphNodeSnapshot:
    return GraphNodeSnapshot(
        node_key=f"organization:{record.id}",
        node_type=GraphNodeType.ORGANIZATION,
        display_name=record.canonical_name,
        source_module="organizations",
        source_entity_type="organization",
        source_record_key=str(record.id),
        source_entity_id=record.id,
        organization_id=record.id,
        observed_at=record.updated_at,
        valid_from=record.created_at,
        confidence=1.0,
    )


def _identity_node(record: OrganizationIdentityRecord) -> GraphNodeSnapshot:
    return GraphNodeSnapshot(
        node_key=f"identity:{record.id}",
        node_type=_IDENTITY_NODE_TYPES.get(record.kind, GraphNodeType.ORGANIZATION),
        display_name=record.official_name,
        source_module="organization_identity",
        source_entity_type=record.kind,
        source_record_key=f"{record.source_id}:{record.source_record_key}",
        source_entity_id=record.id,
        organization_id=record.organization_id,
        source_url=record.source_url,
        observed_at=record.observed_at,
        valid_from=_date_to_datetime(record.valid_from),
        valid_until=_date_to_datetime(record.valid_until),
        confidence=record.confidence,
        active=record.status != "inactive",
    )


def _identity_binding_edge(record: OrganizationIdentityRecord) -> GraphEdgeSnapshot:
    assert record.organization_id is not None
    return GraphEdgeSnapshot(
        edge_key=f"identity-binding:{record.id}:{record.organization_id}",
        source_node_key=f"identity:{record.id}",
        target_node_key=f"organization:{record.organization_id}",
        edge_type=GraphEdgeType.IDENTITY_OF,
        source_module="organization_identity",
        source_record_key=f"identity-binding:{record.id}:{record.organization_id}",
        source_evidence_class="resolved_identity",
        claim_type=GraphClaimType.ASSERTION,
        review_state=GraphReviewState.CONFIRMED,
        observed_at=record.updated_at,
        source_url=record.source_url,
        valid_from=_date_to_datetime(record.valid_from),
        valid_until=_date_to_datetime(record.valid_until),
        confidence=record.confidence,
    )


def _structural_edge(record: OrganizationRelationshipRecord) -> GraphEdgeSnapshot | None:
    edge_type = _RELATIONSHIP_EDGE_TYPES.get(record.relationship_type)
    if edge_type is None:
        return None
    return GraphEdgeSnapshot(
        edge_key=(
            f"identity-relationship:{record.subject_identity_id}:"
            f"{record.object_identity_id}:{record.relationship_type}"
        ),
        source_node_key=f"identity:{record.subject_identity_id}",
        target_node_key=f"identity:{record.object_identity_id}",
        edge_type=edge_type,
        source_module="organization_identity",
        source_record_key=str(record.id),
        source_evidence_class="structural_claim",
        claim_type=GraphClaimType.ASSERTION,
        review_state=GraphReviewState.CONFIRMED,
        observed_at=record.observed_at,
        source_url=record.source_url,
        valid_from=_date_to_datetime(record.valid_from),
        valid_until=_date_to_datetime(record.valid_until),
        confidence=record.confidence,
    )


def _domain_node(record: OrganizationRecord, domain: str) -> GraphNodeSnapshot:
    return GraphNodeSnapshot(
        node_key=f"domain:{domain}",
        node_type=GraphNodeType.DOMAIN,
        display_name=domain,
        source_module="organizations",
        source_entity_type="website_domain",
        source_record_key=f"organization-website:{record.id}:{domain}",
        organization_id=record.id,
        source_url=record.website_url,
        observed_at=record.updated_at,
        confidence=0.9,
    )


def _organization_domain_edge(record: OrganizationRecord, domain: str) -> GraphEdgeSnapshot:
    return GraphEdgeSnapshot(
        edge_key=f"organization-domain:{record.id}:{domain}",
        source_node_key=f"organization:{record.id}",
        target_node_key=f"domain:{domain}",
        edge_type=GraphEdgeType.USES_DOMAIN,
        source_module="organizations",
        source_record_key=f"organization-website:{record.id}:{domain}",
        source_evidence_class="declared_website",
        claim_type=GraphClaimType.ASSERTION,
        review_state=GraphReviewState.UNREVIEWED,
        observed_at=record.updated_at,
        source_url=record.website_url,
        confidence=0.9,
    )


def _website_domain(url: str | None) -> str | None:
    if url is None:
        return None
    value = url.strip()
    if not value:
        return None
    parsed = urlparse(value if "://" in value else f"https://{value}")
    hostname = parsed.hostname
    if hostname is None:
        return None
    normalized = hostname.casefold().rstrip(".")
    return normalized[4:] if normalized.startswith("www.") else normalized


def _date_to_datetime(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.min, tzinfo=UTC)

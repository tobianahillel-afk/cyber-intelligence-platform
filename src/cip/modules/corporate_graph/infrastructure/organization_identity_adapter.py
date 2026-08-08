from __future__ import annotations

from datetime import UTC, date, datetime, time

from cip.modules.corporate_graph.application.batches import GraphProjectionBatch
from cip.modules.corporate_graph.domain.models import (
    GraphClaimType,
    GraphEdgeSnapshot,
    GraphEdgeType,
    GraphNodeSnapshot,
    GraphNodeType,
    GraphReviewState,
)
from cip.modules.corporate_graph.domain.structure import structural_edge_type
from cip.modules.organizations.infrastructure.identity_models import (
    OrganizationIdentityRecord,
    OrganizationRelationshipRecord,
)

_IDENTITY_NODE_TYPES = {
    "legal_unit": GraphNodeType.ORGANIZATION,
    "establishment": GraphNodeType.ESTABLISHMENT,
    "brand": GraphNodeType.BRAND,
    "group": GraphNodeType.GROUP,
}


def project_organization_identities(
    identities: tuple[OrganizationIdentityRecord, ...],
    relationships: tuple[OrganizationRelationshipRecord, ...],
) -> GraphProjectionBatch:
    nodes = tuple(_identity_node(identity) for identity in identities)
    edges: list[GraphEdgeSnapshot] = []
    for identity in identities:
        if identity.organization_id is not None:
            edges.append(_identity_binding_edge(identity))
    for relationship in relationships:
        edge = _structural_edge(relationship)
        if edge is not None:
            edges.append(edge)
    return GraphProjectionBatch(nodes=nodes, edges=tuple(edges))


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
    edge_type = structural_edge_type(record.relationship_type)
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


def _date_to_datetime(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.min, tzinfo=UTC)

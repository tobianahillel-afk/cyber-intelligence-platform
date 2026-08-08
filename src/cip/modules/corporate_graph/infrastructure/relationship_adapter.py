from __future__ import annotations

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
from cip.modules.relationship_intelligence.infrastructure.models import (
    RelationshipEvidenceSnapshotRecord,
)

_ROLE_EDGES = {
    "provider": GraphEdgeType.PROVIDES_TO,
    "customer": GraphEdgeType.CUSTOMER_OF,
    "partner": GraphEdgeType.PARTNER_OF,
    "supplier": GraphEdgeType.SUPPLIES_TO,
    "reseller": GraphEdgeType.RESELLS_TO,
    "distributor": GraphEdgeType.DISTRIBUTES_TO,
    "integrator": GraphEdgeType.INTEGRATES_FOR,
    "auditor": GraphEdgeType.AUDITS,
    "insurer": GraphEdgeType.INSURES,
    "mssp_mdr": GraphEdgeType.SECURES,
    "cloud_hosting_provider": GraphEdgeType.HOSTS_FOR,
    "technology_vendor": GraphEdgeType.PROVIDES_TO,
    "subcontractor": GraphEdgeType.SUBCONTRACTS_FOR,
    "other": GraphEdgeType.RELATED_TO,
}
_CLAIM_TYPES = {
    "assertion": GraphClaimType.ASSERTION,
    "dispute": GraphClaimType.DISPUTE,
    "correction": GraphClaimType.CORRECTION,
    "retraction": GraphClaimType.RETRACTION,
}


def load_relationship_graph(session: Session) -> GraphProjectionBatch:
    snapshots = tuple(session.scalars(select(RelationshipEvidenceSnapshotRecord)).all())
    nodes: list[GraphNodeSnapshot] = []
    edges: list[GraphEdgeSnapshot] = []
    for snapshot in snapshots:
        nodes.extend(_endpoint_nodes(snapshot))
        edges.append(_relationship_edge(snapshot))
        edges.extend(_identity_edges(snapshot))
    return GraphProjectionBatch(nodes=tuple(nodes), edges=tuple(edges))


def _endpoint_nodes(
    record: RelationshipEvidenceSnapshotRecord,
) -> tuple[GraphNodeSnapshot, GraphNodeSnapshot]:
    source_key = _endpoint_key(record.relationship_key, "source")
    target_key = _endpoint_key(record.relationship_key, "target")
    source_name = record.claimed_source_organization_name or _resolved_name(
        record.source_organization_id
    )
    target_name = record.claimed_target_organization_name or _resolved_name(
        record.target_organization_id
    )
    return (
        _endpoint_node(
            node_key=source_key,
            display_name=source_name,
            organization_id=record.source_organization_id,
            record=record,
            side="source",
        ),
        _endpoint_node(
            node_key=target_key,
            display_name=target_name,
            organization_id=record.target_organization_id,
            record=record,
            side="target",
        ),
    )


def _endpoint_node(
    *,
    node_key: str,
    display_name: str,
    organization_id: object,
    record: RelationshipEvidenceSnapshotRecord,
    side: str,
) -> GraphNodeSnapshot:
    return GraphNodeSnapshot(
        node_key=node_key,
        node_type=GraphNodeType.ORGANIZATION,
        display_name=display_name,
        source_module="relationship_intelligence",
        source_entity_type=f"relationship_{side}_endpoint",
        source_record_key=f"{record.source_record_key}:{side}",
        organization_id=organization_id,
        source_url=record.source_url,
        observed_at=record.observed_at,
        valid_from=record.valid_from,
        valid_until=record.valid_until,
        confidence=record.confidence,
        active=record.active,
        metadata_only=record.metadata_only,
    )


def _relationship_edge(record: RelationshipEvidenceSnapshotRecord) -> GraphEdgeSnapshot:
    return GraphEdgeSnapshot(
        edge_key=f"business-relationship:{record.relationship_key}",
        source_node_key=_endpoint_key(record.relationship_key, "source"),
        target_node_key=_endpoint_key(record.relationship_key, "target"),
        edge_type=_ROLE_EDGES.get(record.role, GraphEdgeType.RELATED_TO),
        source_module="relationship_intelligence",
        source_record_key=record.source_record_key,
        source_evidence_class=record.evidence_class,
        claim_type=_CLAIM_TYPES.get(record.claim_type, GraphClaimType.ASSERTION),
        review_state=_relationship_review_state(record),
        observed_at=record.observed_at,
        source_url=record.source_url,
        valid_from=record.valid_from,
        valid_until=record.valid_until,
        expires_at=record.expires_at,
        confidence=record.confidence,
        active=record.active and not record.historical_only,
        supersedes_record_key=record.supersedes_record_key,
    )


def _identity_edges(record: RelationshipEvidenceSnapshotRecord) -> tuple[GraphEdgeSnapshot, ...]:
    edges: list[GraphEdgeSnapshot] = []
    for side, organization_id, link_status in (
        ("source", record.source_organization_id, record.source_link_status),
        ("target", record.target_organization_id, record.target_link_status),
    ):
        if organization_id is None:
            continue
        edges.append(
            GraphEdgeSnapshot(
                edge_key=(
                    f"relationship-endpoint-binding:{record.relationship_key}:"
                    f"{side}:{organization_id}"
                ),
                source_node_key=_endpoint_key(record.relationship_key, side),
                target_node_key=f"organization:{organization_id}",
                edge_type=GraphEdgeType.IDENTITY_OF,
                source_module="relationship_intelligence",
                source_record_key=f"{record.source_record_key}:{side}:identity",
                source_evidence_class="endpoint_resolution",
                claim_type=_CLAIM_TYPES.get(record.claim_type, GraphClaimType.ASSERTION),
                review_state=_link_review_state(link_status),
                observed_at=record.observed_at,
                source_url=record.source_url,
                valid_from=record.valid_from,
                valid_until=record.valid_until,
                expires_at=record.expires_at,
                confidence=record.confidence,
                active=record.active,
                supersedes_record_key=(
                    f"{record.supersedes_record_key}:{side}:identity"
                    if record.supersedes_record_key
                    else None
                ),
            )
        )
    return tuple(edges)


def _relationship_review_state(record: RelationshipEvidenceSnapshotRecord) -> GraphReviewState:
    statuses = {record.source_link_status, record.target_link_status}
    if "rejected" in statuses:
        return GraphReviewState.REJECTED
    if statuses & {"candidate", "review_required", "unresolved"}:
        return GraphReviewState.REVIEW_REQUIRED
    if record.evidence_class in {"observed", "contracted"}:
        return GraphReviewState.CONFIRMED
    if record.evidence_class == "inferred":
        return GraphReviewState.REVIEW_REQUIRED
    return GraphReviewState.UNREVIEWED


def _link_review_state(link_status: str) -> GraphReviewState:
    if link_status == "exact":
        return GraphReviewState.CONFIRMED
    if link_status == "rejected":
        return GraphReviewState.REJECTED
    return GraphReviewState.REVIEW_REQUIRED


def _endpoint_key(relationship_key: str, side: str) -> str:
    return f"relationship-endpoint:{relationship_key}:{side}"


def _resolved_name(organization_id: object) -> str:
    if organization_id is None:
        return "Unresolved organization"
    return f"Resolved organization {organization_id}"

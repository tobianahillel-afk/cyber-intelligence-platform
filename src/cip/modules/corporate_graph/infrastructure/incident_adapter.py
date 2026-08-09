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
from cip.modules.incident_intelligence.infrastructure.models import IncidentClaimSnapshotRecord

_CLAIM_TYPES = {
    "denial": GraphClaimType.DISPUTE,
    "correction": GraphClaimType.CORRECTION,
    "retraction": GraphClaimType.RETRACTION,
}


def load_incident_graph(session: Session) -> GraphProjectionBatch:
    claims = tuple(session.scalars(select(IncidentClaimSnapshotRecord)).all())
    nodes: list[GraphNodeSnapshot] = []
    edges: list[GraphEdgeSnapshot] = []
    for claim in claims:
        nodes.append(_incident_node(claim))
        edge = _organization_edge(claim)
        if edge is not None:
            edges.append(edge)
    return GraphProjectionBatch(nodes=tuple(nodes), edges=tuple(edges))


def _incident_node(record: IncidentClaimSnapshotRecord) -> GraphNodeSnapshot:
    claim_type = _claim_type(record.claim_type)
    return GraphNodeSnapshot(
        node_key=f"incident:{record.incident_id}",
        node_type=GraphNodeType.INCIDENT,
        display_name=record.title,
        source_module="incident_intelligence",
        source_entity_type=record.incident_type,
        source_record_key=record.source_record_key,
        source_entity_id=record.incident_id,
        organization_id=(
            record.organization_id if record.organization_link_status == "exact" else None
        ),
        source_url=record.source_url,
        observed_at=record.modified_at,
        valid_from=record.occurrence_start_at,
        valid_until=record.occurrence_end_at,
        confidence=record.confidence,
        active=(
            record.active
            and not record.historical_only
            and claim_type not in {GraphClaimType.RETRACTION, GraphClaimType.DISPUTE}
        ),
        metadata_only=record.metadata_only,
    )


def _organization_edge(record: IncidentClaimSnapshotRecord) -> GraphEdgeSnapshot | None:
    if record.organization_id is None or record.organization_link_status != "exact":
        return None
    return GraphEdgeSnapshot(
        edge_key=f"incident-organization:{record.incident_id}:{record.organization_id}",
        source_node_key=f"incident:{record.incident_id}",
        target_node_key=f"organization:{record.organization_id}",
        edge_type=GraphEdgeType.INCIDENT_INVOLVES,
        source_module="incident_intelligence",
        source_record_key=record.source_record_key,
        source_evidence_class=record.claim_type,
        claim_type=_claim_type(record.claim_type),
        review_state=GraphReviewState.CONFIRMED,
        source_url=record.source_url,
        observed_at=record.modified_at,
        valid_from=record.occurrence_start_at,
        valid_until=record.occurrence_end_at,
        confidence=record.confidence,
        active=record.active and not record.historical_only,
        supersedes_record_key=record.supersedes_record_key,
    )


def _claim_type(value: str) -> GraphClaimType:
    return _CLAIM_TYPES.get(value, GraphClaimType.ASSERTION)

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.corporate_changes.infrastructure.models import CorporateChangeClaimSnapshotRecord
from cip.modules.corporate_graph.application.batches import GraphProjectionBatch
from cip.modules.corporate_graph.domain.models import (
    GraphClaimType,
    GraphEdgeSnapshot,
    GraphEdgeType,
    GraphNodeSnapshot,
    GraphNodeType,
    GraphReviewState,
)

_CLAIM_TYPES = {
    "dispute": GraphClaimType.DISPUTE,
    "correction": GraphClaimType.CORRECTION,
    "retraction": GraphClaimType.RETRACTION,
}


def load_corporate_change_graph(session: Session) -> GraphProjectionBatch:
    claims = tuple(session.scalars(select(CorporateChangeClaimSnapshotRecord)).all())
    nodes: list[GraphNodeSnapshot] = []
    edges: list[GraphEdgeSnapshot] = []
    for claim in claims:
        nodes.append(_change_node(claim))
        edge = _organization_edge(claim)
        if edge is not None:
            edges.append(edge)
    return GraphProjectionBatch(nodes=tuple(nodes), edges=tuple(edges))


def _change_node(record: CorporateChangeClaimSnapshotRecord) -> GraphNodeSnapshot:
    claim_type = _claim_type(record.claim_type)
    return GraphNodeSnapshot(
        node_key=f"material-change:{record.event_id}",
        node_type=GraphNodeType.MATERIAL_CHANGE,
        display_name=record.title,
        source_module="corporate_changes",
        source_entity_type=record.event_type,
        source_record_key=record.source_record_key,
        source_entity_id=record.event_id,
        organization_id=(
            record.organization_id if record.organization_link_status == "exact" else None
        ),
        source_url=record.source_url,
        observed_at=record.modified_at,
        valid_from=record.event_at,
        valid_until=record.expires_at,
        confidence=record.confidence,
        active=(
            record.active
            and not record.historical_only
            and claim_type not in {GraphClaimType.RETRACTION, GraphClaimType.DISPUTE}
        ),
        metadata_only=record.metadata_only,
    )


def _organization_edge(
    record: CorporateChangeClaimSnapshotRecord,
) -> GraphEdgeSnapshot | None:
    if record.organization_id is None or record.organization_link_status != "exact":
        return None
    return GraphEdgeSnapshot(
        edge_key=f"material-change-organization:{record.event_id}:{record.organization_id}",
        source_node_key=f"material-change:{record.event_id}",
        target_node_key=f"organization:{record.organization_id}",
        edge_type=GraphEdgeType.MATERIAL_CHANGE_AFFECTS,
        source_module="corporate_changes",
        source_record_key=record.source_record_key,
        source_evidence_class=f"{record.source_kind}:{record.claim_type}",
        claim_type=_claim_type(record.claim_type),
        review_state=_review_state(record.claim_type),
        source_url=record.source_url,
        observed_at=record.modified_at,
        valid_from=record.event_at,
        valid_until=record.expires_at,
        expires_at=record.expires_at,
        confidence=record.confidence,
        active=record.active and not record.historical_only,
        supersedes_record_key=record.supersedes_record_key,
    )


def _claim_type(value: str) -> GraphClaimType:
    return _CLAIM_TYPES.get(value, GraphClaimType.ASSERTION)


def _review_state(value: str) -> GraphReviewState:
    if value in {"official_confirmation", "regulator_notice", "company_disclosure"}:
        return GraphReviewState.CONFIRMED
    if value in {"speculation", "dispute"}:
        return GraphReviewState.REVIEW_REQUIRED
    if value == "retraction":
        return GraphReviewState.REJECTED
    return GraphReviewState.UNREVIEWED

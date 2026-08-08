from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.corporate_graph.domain.models import (
    GraphClaimType,
    GraphEdgeSnapshot,
    GraphEdgeType,
    GraphNodeSnapshot,
    GraphNodeType,
    GraphReviewState,
)
from cip.modules.corporate_graph.infrastructure.models import (
    CorporateGraphEdgeSnapshotRecord,
    CorporateGraphNodeSnapshotRecord,
)


def node_snapshots(session: Session, node_id: UUID) -> tuple[GraphNodeSnapshot, ...]:
    records = session.scalars(
        select(CorporateGraphNodeSnapshotRecord)
        .where(CorporateGraphNodeSnapshotRecord.node_id == node_id)
        .order_by(CorporateGraphNodeSnapshotRecord.observed_at)
    ).all()
    return tuple(_node_snapshot(record) for record in records)


def edge_snapshots(session: Session, edge_id: UUID) -> tuple[GraphEdgeSnapshot, ...]:
    records = session.scalars(
        select(CorporateGraphEdgeSnapshotRecord)
        .where(CorporateGraphEdgeSnapshotRecord.edge_id == edge_id)
        .order_by(CorporateGraphEdgeSnapshotRecord.observed_at)
    ).all()
    return tuple(_edge_snapshot(record) for record in records)


def _node_snapshot(record: CorporateGraphNodeSnapshotRecord) -> GraphNodeSnapshot:
    return GraphNodeSnapshot(
        node_key=record.node_key,
        node_type=GraphNodeType(record.node_type),
        display_name=record.display_name,
        source_module=record.source_module,
        source_entity_type=record.source_entity_type,
        source_record_key=record.source_record_key,
        source_entity_id=record.source_entity_id,
        organization_id=record.organization_id,
        source_url=record.source_url,
        observed_at=record.observed_at,
        valid_from=record.valid_from,
        valid_until=record.valid_until,
        confidence=record.confidence,
        active=record.active,
        suppressed=record.suppressed,
        metadata_only=record.metadata_only,
    )


def _edge_snapshot(record: CorporateGraphEdgeSnapshotRecord) -> GraphEdgeSnapshot:
    return GraphEdgeSnapshot(
        edge_key=record.edge_key,
        source_node_key=record.source_node_key,
        target_node_key=record.target_node_key,
        edge_type=GraphEdgeType(record.edge_type),
        source_module=record.source_module,
        source_record_key=record.source_record_key,
        source_evidence_class=record.source_evidence_class,
        claim_type=GraphClaimType(record.claim_type),
        review_state=GraphReviewState(record.review_state),
        source_url=record.source_url,
        observed_at=record.observed_at,
        valid_from=record.valid_from,
        valid_until=record.valid_until,
        expires_at=record.expires_at,
        confidence=record.confidence,
        active=record.active,
        suppressed=record.suppressed,
        supersedes_record_key=record.supersedes_record_key,
    )

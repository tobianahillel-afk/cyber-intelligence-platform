from __future__ import annotations

from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.corporate_graph.domain.models import GraphEdgeSnapshot, GraphNodeSnapshot
from cip.modules.corporate_graph.domain.reconciliation import reconcile_edge_snapshots
from cip.modules.corporate_graph.infrastructure.models import (
    CorporateGraphEdgeRecord,
    CorporateGraphEdgeSnapshotRecord,
    CorporateGraphNodeRecord,
    CorporateGraphNodeSnapshotRecord,
)
from cip.modules.corporate_graph.infrastructure.node_state import refresh_node_state
from cip.modules.corporate_graph.infrastructure.projection_hydration import edge_snapshots
from cip.modules.corporate_graph.infrastructure.projection_payloads import (
    graph_edge_digest,
    graph_node_digest,
)
from cip.shared.kernel.time import require_aware_utc


def persist_graph_nodes(
    session: Session,
    snapshots: tuple[GraphNodeSnapshot, ...],
    *,
    now: datetime,
) -> tuple[UUID, ...]:
    persisted_at = require_aware_utc(now, field_name="now")
    touched: set[UUID] = set()
    for snapshot in snapshots:
        node = _resolve_node(session, snapshot, now=persisted_at)
        _insert_node_snapshot(session, node.id, snapshot, now=persisted_at)
        touched.add(node.id)
    for node_id in touched:
        refresh_node_state(session, node_id, now=persisted_at)
    session.flush()
    return tuple(sorted(touched, key=str))


def persist_graph_edges(
    session: Session,
    snapshots: tuple[GraphEdgeSnapshot, ...],
    *,
    now: datetime,
) -> tuple[UUID, ...]:
    persisted_at = require_aware_utc(now, field_name="now")
    touched: set[UUID] = set()
    for snapshot in snapshots:
        _require_node(session, snapshot.source_node_key)
        _require_node(session, snapshot.target_node_key)
        edge = _resolve_edge(session, snapshot, now=persisted_at)
        _insert_edge_snapshot(session, edge.id, snapshot, now=persisted_at)
        touched.add(edge.id)
    for edge_id in touched:
        _refresh_edge(session, edge_id, now=persisted_at)
    session.flush()
    return tuple(sorted(touched, key=str))


def _resolve_node(
    session: Session,
    snapshot: GraphNodeSnapshot,
    *,
    now: datetime,
) -> CorporateGraphNodeRecord:
    existing = session.scalar(
        select(CorporateGraphNodeRecord).where(
            CorporateGraphNodeRecord.node_key == snapshot.node_key
        )
    )
    if existing is not None:
        if existing.node_type != snapshot.node_type.value:
            raise ValueError("graph node key cannot change node type")
        return existing
    record = CorporateGraphNodeRecord(
        id=uuid5(NAMESPACE_URL, f"corporate-graph-node:{snapshot.node_key}"),
        node_key=snapshot.node_key,
        node_type=snapshot.node_type.value,
        display_name=snapshot.display_name,
        organization_id=snapshot.organization_id,
        source_count=1,
        confidence=snapshot.confidence,
        current=snapshot.active and not snapshot.suppressed,
        suppressed=snapshot.suppressed,
        first_observed_at=snapshot.observed_at,
        last_observed_at=snapshot.observed_at,
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    session.flush()
    return record


def _insert_node_snapshot(
    session: Session,
    node_id: UUID,
    snapshot: GraphNodeSnapshot,
    *,
    now: datetime,
) -> CorporateGraphNodeSnapshotRecord:
    digest = graph_node_digest(snapshot)
    existing = session.scalar(
        select(CorporateGraphNodeSnapshotRecord).where(
            CorporateGraphNodeSnapshotRecord.snapshot_key == digest
        )
    )
    if existing is not None:
        if existing.node_id != node_id:
            raise ValueError("graph node snapshot cannot move between nodes")
        return existing
    record = CorporateGraphNodeSnapshotRecord(
        id=uuid5(NAMESPACE_URL, f"corporate-graph-node-snapshot:{digest}"),
        node_id=node_id,
        snapshot_key=digest,
        node_key=snapshot.node_key,
        node_type=snapshot.node_type.value,
        display_name=snapshot.display_name,
        source_module=snapshot.source_module,
        source_entity_type=snapshot.source_entity_type,
        source_record_key=snapshot.source_record_key,
        source_entity_id=snapshot.source_entity_id,
        organization_id=snapshot.organization_id,
        source_url=snapshot.source_url,
        observed_at=snapshot.observed_at,
        valid_from=snapshot.valid_from,
        valid_until=snapshot.valid_until,
        confidence=snapshot.confidence,
        active=snapshot.active,
        suppressed=snapshot.suppressed,
        metadata_only=snapshot.metadata_only,
        created_at=now,
    )
    session.add(record)
    session.flush()
    return record


def _resolve_edge(
    session: Session,
    snapshot: GraphEdgeSnapshot,
    *,
    now: datetime,
) -> CorporateGraphEdgeRecord:
    existing = session.scalar(
        select(CorporateGraphEdgeRecord).where(
            CorporateGraphEdgeRecord.edge_key == snapshot.edge_key
        )
    )
    if existing is not None:
        identity = (existing.source_node_key, existing.target_node_key, existing.edge_type)
        expected = (
            snapshot.source_node_key,
            snapshot.target_node_key,
            snapshot.edge_type.value,
        )
        if identity != expected:
            raise ValueError("graph edge key cannot change direction or type")
        return existing
    record = CorporateGraphEdgeRecord(
        id=uuid5(NAMESPACE_URL, f"corporate-graph-edge:{snapshot.edge_key}"),
        edge_key=snapshot.edge_key,
        source_node_key=snapshot.source_node_key,
        target_node_key=snapshot.target_node_key,
        edge_type=snapshot.edge_type.value,
        source_module=snapshot.source_module,
        source_evidence_class=snapshot.source_evidence_class,
        review_state=snapshot.review_state.value,
        confidence=snapshot.confidence,
        current=snapshot.active and not snapshot.suppressed,
        suppressed=snapshot.suppressed,
        valid_from=snapshot.valid_from,
        valid_until=snapshot.valid_until,
        first_observed_at=snapshot.observed_at,
        last_observed_at=snapshot.observed_at,
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    session.flush()
    return record


def _insert_edge_snapshot(
    session: Session,
    edge_id: UUID,
    snapshot: GraphEdgeSnapshot,
    *,
    now: datetime,
) -> CorporateGraphEdgeSnapshotRecord:
    digest = graph_edge_digest(snapshot)
    existing = session.scalar(
        select(CorporateGraphEdgeSnapshotRecord).where(
            CorporateGraphEdgeSnapshotRecord.snapshot_key == digest
        )
    )
    if existing is not None:
        if existing.edge_id != edge_id:
            raise ValueError("graph edge snapshot cannot move between edges")
        return existing
    record = CorporateGraphEdgeSnapshotRecord(
        id=uuid5(NAMESPACE_URL, f"corporate-graph-edge-snapshot:{digest}"),
        edge_id=edge_id,
        snapshot_key=digest,
        edge_key=snapshot.edge_key,
        source_node_key=snapshot.source_node_key,
        target_node_key=snapshot.target_node_key,
        edge_type=snapshot.edge_type.value,
        source_module=snapshot.source_module,
        source_record_key=snapshot.source_record_key,
        source_evidence_class=snapshot.source_evidence_class,
        claim_type=snapshot.claim_type.value,
        review_state=snapshot.review_state.value,
        source_url=snapshot.source_url,
        observed_at=snapshot.observed_at,
        valid_from=snapshot.valid_from,
        valid_until=snapshot.valid_until,
        expires_at=snapshot.expires_at,
        confidence=snapshot.confidence,
        active=snapshot.active,
        suppressed=snapshot.suppressed,
        supersedes_record_key=snapshot.supersedes_record_key,
        created_at=now,
    )
    session.add(record)
    session.flush()
    return record


def _refresh_edge(session: Session, edge_id: UUID, *, now: datetime) -> None:
    record = session.get(CorporateGraphEdgeRecord, edge_id)
    if record is None:
        raise ValueError("graph edge disappeared during reconciliation")
    projection = reconcile_edge_snapshots(edge_snapshots(session, edge_id), now=now)
    record.source_module = projection.source_module
    record.source_evidence_class = projection.source_evidence_class
    record.review_state = projection.review_state.value
    record.confidence = projection.confidence
    record.current = projection.current
    record.suppressed = projection.suppressed
    record.valid_from = projection.valid_from
    record.valid_until = projection.valid_until
    record.first_observed_at = projection.first_observed_at
    record.last_observed_at = projection.last_observed_at
    record.updated_at = now


def _require_node(session: Session, node_key: str) -> None:
    node = session.scalar(
        select(CorporateGraphNodeRecord.id).where(CorporateGraphNodeRecord.node_key == node_key)
    )
    if node is None:
        raise ValueError(f"graph edge references missing node: {node_key}")

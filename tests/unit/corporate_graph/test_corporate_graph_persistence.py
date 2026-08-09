from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from cip.modules.corporate_graph.domain.models import (
    GraphClaimType,
    GraphEdgeSnapshot,
    GraphEdgeType,
    GraphNodeSnapshot,
    GraphNodeType,
    GraphReviewState,
)
from cip.modules.corporate_graph.infrastructure.models import (
    CorporateGraphEdgeRecord,
    CorporateGraphEdgeSnapshotRecord,
    CorporateGraphNodeRecord,
    CorporateGraphNodeSnapshotRecord,
)
from cip.modules.corporate_graph.infrastructure.projections import (
    persist_graph_edges,
    persist_graph_nodes,
)
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 8, 21, 0, tzinfo=UTC)


def test_graph_snapshot_replay_is_idempotent() -> None:
    session = _session()
    nodes = (_node("brand:a", "A"), _node("brand:b", "B"))
    edge = _edge("brand:a", "brand:b")

    persist_graph_nodes(session, nodes, now=NOW)
    persist_graph_edges(session, (edge,), now=NOW)
    persist_graph_nodes(session, nodes, now=NOW)
    persist_graph_edges(session, (edge,), now=NOW)

    assert _count(session, CorporateGraphNodeRecord) == 2
    assert _count(session, CorporateGraphNodeSnapshotRecord) == 2
    assert _count(session, CorporateGraphEdgeRecord) == 1
    assert _count(session, CorporateGraphEdgeSnapshotRecord) == 1


def test_edge_identity_cannot_silently_change_direction() -> None:
    session = _session()
    persist_graph_nodes(
        session,
        (_node("brand:a", "A"), _node("brand:b", "B")),
        now=NOW,
    )
    persist_graph_edges(session, (_edge("brand:a", "brand:b"),), now=NOW)

    with pytest.raises(ValueError, match="direction or type"):
        persist_graph_edges(session, (_edge("brand:b", "brand:a"),), now=NOW)


def test_retraction_preserves_two_immutable_edge_snapshots() -> None:
    session = _session()
    persist_graph_nodes(
        session,
        (_node("brand:a", "A"), _node("brand:b", "B")),
        now=NOW,
    )
    original = _edge("brand:a", "brand:b", source_record_key="record-1")
    retraction = _edge(
        "brand:a",
        "brand:b",
        source_record_key="record-2",
        claim_type=GraphClaimType.RETRACTION,
        review_state=GraphReviewState.REJECTED,
        supersedes_record_key="record-1",
    )

    persist_graph_edges(session, (original,), now=NOW)
    persist_graph_edges(session, (retraction,), now=NOW)
    record = session.scalar(select(CorporateGraphEdgeRecord))

    assert record is not None
    assert not record.current
    assert _count(session, CorporateGraphEdgeSnapshotRecord) == 2


def _session():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return create_session_factory(engine)()


def _count(session, model) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def _node(node_key: str, display_name: str) -> GraphNodeSnapshot:
    return GraphNodeSnapshot(
        node_key=node_key,
        node_type=GraphNodeType.BRAND,
        display_name=display_name,
        source_module="test",
        source_entity_type="brand",
        source_record_key=node_key,
        observed_at=NOW,
        confidence=0.8,
    )


def _edge(
    source_node_key: str,
    target_node_key: str,
    *,
    source_record_key: str = "record-1",
    claim_type: GraphClaimType = GraphClaimType.ASSERTION,
    review_state: GraphReviewState = GraphReviewState.CONFIRMED,
    supersedes_record_key: str | None = None,
) -> GraphEdgeSnapshot:
    return GraphEdgeSnapshot(
        edge_key="relationship:a:b",
        source_node_key=source_node_key,
        target_node_key=target_node_key,
        edge_type=GraphEdgeType.PARTNER_OF,
        source_module="test",
        source_record_key=source_record_key,
        source_evidence_class="observed",
        claim_type=claim_type,
        review_state=review_state,
        observed_at=NOW,
        confidence=0.8,
        supersedes_record_key=supersedes_record_key,
    )

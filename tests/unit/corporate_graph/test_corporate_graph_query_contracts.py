from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cip.modules.corporate_graph.application.view_models import GraphNodeFilters
from cip.modules.corporate_graph.domain.models import GraphNodeSnapshot, GraphNodeType
from cip.modules.corporate_graph.infrastructure.projections import persist_graph_nodes
from cip.modules.corporate_graph.infrastructure.queries import list_graph_nodes
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 8, 21, 0, tzinfo=UTC)


def test_graph_reads_are_bounded_and_paginate_without_overlap() -> None:
    session = _session()
    snapshots = tuple(_node(index) for index in range(220))
    persist_graph_nodes(session, snapshots, now=NOW)

    first = list_graph_nodes(
        session,
        filters=GraphNodeFilters(),
        limit=200,
        offset=0,
    )
    second = list_graph_nodes(
        session,
        filters=GraphNodeFilters(),
        limit=200,
        offset=200,
    )

    assert first.total == 220
    assert len(first.items) == 200
    assert len(second.items) == 20
    assert {item.node_key for item in first.items}.isdisjoint(
        {item.node_key for item in second.items}
    )


def test_graph_reads_reject_unbounded_limits() -> None:
    session = _session()

    with pytest.raises(ValueError, match="between 1 and 200"):
        list_graph_nodes(
            session,
            filters=GraphNodeFilters(),
            limit=201,
            offset=0,
        )


def _session():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return create_session_factory(engine)()


def _node(index: int) -> GraphNodeSnapshot:
    return GraphNodeSnapshot(
        node_key=f"brand:benchmark:{index:03d}",
        node_type=GraphNodeType.BRAND,
        display_name=f"Benchmark {index:03d}",
        source_module="benchmark",
        source_entity_type="brand",
        source_record_key=f"benchmark:{index:03d}",
        observed_at=NOW,
        confidence=0.5,
    )

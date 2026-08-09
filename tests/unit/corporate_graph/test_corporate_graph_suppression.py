from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from cip.modules.corporate_graph.domain.models import GraphNodeSnapshot, GraphNodeType
from cip.modules.corporate_graph.infrastructure.models import (
    CorporateGraphNodeRecord,
    CorporateGraphNodeSnapshotRecord,
)
from cip.modules.corporate_graph.infrastructure.projections import persist_graph_nodes
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 8, 21, 0, tzinfo=UTC)


def test_newer_source_suppression_removes_current_node_but_preserves_history() -> None:
    session = _session()
    current = _snapshot(observed_at=NOW - timedelta(days=1), suppressed=False)
    suppressed = _snapshot(observed_at=NOW, suppressed=True)

    persist_graph_nodes(session, (current,), now=NOW)
    persist_graph_nodes(session, (suppressed,), now=NOW)

    node = session.scalar(select(CorporateGraphNodeRecord))
    history_count = session.scalar(
        select(func.count()).select_from(CorporateGraphNodeSnapshotRecord)
    )

    assert node is not None
    assert node.current is False
    assert node.suppressed is True
    assert history_count == 2


def _snapshot(*, observed_at: datetime, suppressed: bool) -> GraphNodeSnapshot:
    return GraphNodeSnapshot(
        node_key="brand:suppression-test",
        node_type=GraphNodeType.BRAND,
        display_name="Suppression Test",
        source_module="source-a",
        source_entity_type="brand",
        source_record_key=f"source-a:{observed_at.isoformat()}",
        observed_at=observed_at,
        confidence=0.9,
        suppressed=suppressed,
    )


def _session():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return create_session_factory(engine)()

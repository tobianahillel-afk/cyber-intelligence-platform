from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from cip.modules.corporate_graph.application.batches import GraphProjectionBatch
from cip.modules.corporate_graph.infrastructure.applicability_adapter import (
    load_applicability_graph,
)
from cip.modules.corporate_graph.infrastructure.corporate_change_adapter import (
    load_corporate_change_graph,
)
from cip.modules.corporate_graph.infrastructure.incident_adapter import load_incident_graph
from cip.modules.corporate_graph.infrastructure.organization_adapter import (
    load_organization_graph,
)
from cip.modules.corporate_graph.infrastructure.passive_adapter import load_passive_graph
from cip.modules.corporate_graph.infrastructure.projections import (
    persist_graph_edges,
    persist_graph_nodes,
)
from cip.modules.corporate_graph.infrastructure.relationship_adapter import (
    load_relationship_graph,
)
from cip.shared.kernel.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class GraphRefreshResult:
    node_ids: tuple[UUID, ...]
    edge_ids: tuple[UUID, ...]
    node_snapshot_count: int
    edge_snapshot_count: int


def refresh_corporate_graph(
    session: Session,
    *,
    now: datetime,
) -> GraphRefreshResult:
    refreshed_at = require_aware_utc(now, field_name="now")
    batch = GraphProjectionBatch()
    for loader in (
        load_organization_graph,
        load_relationship_graph,
        load_passive_graph,
        load_incident_graph,
        load_corporate_change_graph,
        load_applicability_graph,
    ):
        batch = batch.combine(loader(session))
    node_ids = persist_graph_nodes(session, batch.nodes, now=refreshed_at)
    edge_ids = persist_graph_edges(session, batch.edges, now=refreshed_at)
    return GraphRefreshResult(
        node_ids=node_ids,
        edge_ids=edge_ids,
        node_snapshot_count=len(batch.nodes),
        edge_snapshot_count=len(batch.edges),
    )

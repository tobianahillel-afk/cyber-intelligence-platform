from __future__ import annotations

from dataclasses import dataclass

from cip.modules.corporate_graph.domain.models import GraphEdgeSnapshot, GraphNodeSnapshot


@dataclass(frozen=True, slots=True)
class GraphProjectionBatch:
    nodes: tuple[GraphNodeSnapshot, ...] = ()
    edges: tuple[GraphEdgeSnapshot, ...] = ()

    def combine(self, other: GraphProjectionBatch) -> GraphProjectionBatch:
        return GraphProjectionBatch(
            nodes=self.nodes + other.nodes,
            edges=self.edges + other.edges,
        )

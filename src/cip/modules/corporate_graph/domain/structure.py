from __future__ import annotations

from cip.modules.corporate_graph.domain.models import GraphEdgeType

_STRUCTURAL_RELATIONSHIPS = {
    "establishment_of": GraphEdgeType.ESTABLISHMENT_OF,
    "headquarters_of": GraphEdgeType.ESTABLISHMENT_OF,
    "direct_parent": GraphEdgeType.PARENT_OF,
    "ultimate_parent": GraphEdgeType.PARENT_OF,
    "subsidiary": GraphEdgeType.SUBSIDIARY_OF,
    "brand_of": GraphEdgeType.BRAND_OF,
    "predecessor": GraphEdgeType.PREDECESSOR_OF,
    "successor": GraphEdgeType.SUCCESSOR_OF,
    "merged_into": GraphEdgeType.MERGED_INTO,
    "spin_off_of": GraphEdgeType.SPIN_OFF_OF,
}


def structural_edge_type(relationship_type: str) -> GraphEdgeType | None:
    return _STRUCTURAL_RELATIONSHIPS.get(relationship_type.strip().casefold())

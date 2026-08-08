from cip.modules.corporate_graph.domain.models import GraphEdgeType
from cip.modules.corporate_graph.domain.structure import structural_edge_type


def test_merger_and_spin_off_relationships_keep_directional_semantics() -> None:
    assert structural_edge_type("merged_into") is GraphEdgeType.MERGED_INTO
    assert structural_edge_type("spin_off_of") is GraphEdgeType.SPIN_OFF_OF
    assert structural_edge_type("predecessor") is GraphEdgeType.PREDECESSOR_OF
    assert structural_edge_type("successor") is GraphEdgeType.SUCCESSOR_OF


def test_unknown_structural_relationship_is_not_guessed() -> None:
    assert structural_edge_type("looks_related") is None

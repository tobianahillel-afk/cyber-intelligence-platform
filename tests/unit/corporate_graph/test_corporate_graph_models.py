from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cip.modules.corporate_graph.domain.models import (
    GraphClaimType,
    GraphEdgeSnapshot,
    GraphEdgeType,
    GraphNodeSnapshot,
    GraphNodeType,
    GraphReviewState,
)

NOW = datetime(2026, 8, 8, 20, 0, tzinfo=UTC)


def test_node_current_state_respects_suppression_and_validity() -> None:
    current = GraphNodeSnapshot(
        node_key="organization:acme",
        node_type=GraphNodeType.ORGANIZATION,
        display_name="Acme",
        source_module="organizations",
        source_entity_type="organization",
        source_record_key="acme",
        observed_at=NOW,
        confidence=1.0,
    )
    suppressed = GraphNodeSnapshot(
        node_key="organization:old-acme",
        node_type=GraphNodeType.ORGANIZATION,
        display_name="Old Acme",
        source_module="organizations",
        source_entity_type="organization",
        source_record_key="old-acme",
        observed_at=NOW,
        confidence=1.0,
        suppressed=True,
    )

    assert current.is_current_at(NOW)
    assert not suppressed.is_current_at(NOW)


def test_edge_does_not_upgrade_claimed_or_inferred_evidence() -> None:
    for evidence_class in ("claimed", "inferred", "historical"):
        edge = _edge(evidence_class=evidence_class)
        assert edge.preserves_weak_evidence


def test_retracted_or_rejected_edge_is_never_current() -> None:
    retracted = _edge(claim_type=GraphClaimType.RETRACTION)
    rejected = _edge(review_state=GraphReviewState.REJECTED)

    assert not retracted.is_current_at(NOW)
    assert not rejected.is_current_at(NOW)


def test_expired_edge_is_not_current() -> None:
    edge = _edge(expires_at=NOW - timedelta(seconds=1))

    assert not edge.is_current_at(NOW)


def test_self_edge_is_rejected() -> None:
    with pytest.raises(ValueError, match="self-referential"):
        _edge(target_node_key="organization:a")


def _edge(
    *,
    evidence_class: str = "observed",
    claim_type: GraphClaimType = GraphClaimType.ASSERTION,
    review_state: GraphReviewState = GraphReviewState.CONFIRMED,
    target_node_key: str = "organization:b",
    expires_at: datetime | None = None,
) -> GraphEdgeSnapshot:
    return GraphEdgeSnapshot(
        edge_key="relationship:a:b",
        source_node_key="organization:a",
        target_node_key=target_node_key,
        edge_type=GraphEdgeType.PROVIDES_TO,
        source_module="relationship_intelligence",
        source_record_key="relationship:a:b:1",
        source_evidence_class=evidence_class,
        claim_type=claim_type,
        review_state=review_state,
        observed_at=NOW,
        expires_at=expires_at,
        confidence=0.8,
    )

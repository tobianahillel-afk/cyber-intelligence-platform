from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from cip.modules.corporate_graph.domain.models import (
    GraphClaimType,
    GraphEdgeSnapshot,
    GraphEdgeType,
    GraphNodeSnapshot,
    GraphNodeType,
    GraphReviewState,
)
from cip.modules.corporate_graph.domain.reconciliation import (
    reconcile_edge_snapshots,
    reconcile_node_snapshots,
)

NOW = datetime(2026, 8, 8, 21, 0, tzinfo=UTC)


def test_conflicting_current_organization_ids_do_not_force_node_resolution() -> None:
    first = _node(organization_id=uuid4(), source_module="source-a")
    second = _node(organization_id=uuid4(), source_module="source-b")

    projection = reconcile_node_snapshots((first, second), now=NOW)

    assert projection.organization_id is None
    assert projection.source_count == 2
    assert projection.current


def test_source_specific_supersession_removes_old_edge_revision() -> None:
    original = _edge(
        source_record_key="record-1",
        evidence_class="claimed",
        observed_at=NOW - timedelta(days=2),
    )
    correction = _edge(
        source_record_key="record-2",
        evidence_class="observed",
        observed_at=NOW - timedelta(days=1),
        supersedes_record_key="record-1",
    )

    projection = reconcile_edge_snapshots((original, correction), now=NOW)

    assert projection.current
    assert projection.source_evidence_class == "observed"
    assert projection.last_observed_at == correction.observed_at


def test_retraction_makes_edge_non_current_without_deleting_history() -> None:
    original = _edge(
        source_record_key="record-1",
        evidence_class="contracted",
        observed_at=NOW - timedelta(days=2),
    )
    retraction = _edge(
        source_record_key="record-2",
        evidence_class="contracted",
        observed_at=NOW - timedelta(days=1),
        claim_type=GraphClaimType.RETRACTION,
        review_state=GraphReviewState.REJECTED,
        supersedes_record_key="record-1",
    )

    projection = reconcile_edge_snapshots((original, retraction), now=NOW)

    assert not projection.current
    assert projection.review_state is GraphReviewState.REJECTED
    assert projection.first_observed_at == retraction.observed_at


def test_as_of_reconciliation_restores_historical_edge_state() -> None:
    original = _edge(
        source_record_key="record-1",
        evidence_class="observed",
        observed_at=NOW - timedelta(days=3),
    )
    expired = _edge(
        source_record_key="record-2",
        evidence_class="historical",
        observed_at=NOW - timedelta(days=1),
        valid_until=NOW - timedelta(hours=12),
        supersedes_record_key="record-1",
    )

    before = reconcile_edge_snapshots((original,), now=NOW - timedelta(days=2))
    after = reconcile_edge_snapshots((original, expired), now=NOW)

    assert before.current
    assert not after.current
    assert after.source_evidence_class == "historical"


def _node(*, organization_id, source_module: str) -> GraphNodeSnapshot:
    return GraphNodeSnapshot(
        node_key="brand:acme",
        node_type=GraphNodeType.BRAND,
        display_name="Acme",
        source_module=source_module,
        source_entity_type="brand",
        source_record_key=f"{source_module}:acme",
        organization_id=organization_id,
        observed_at=NOW,
        confidence=0.8,
    )


def _edge(
    *,
    source_record_key: str,
    evidence_class: str,
    observed_at: datetime,
    claim_type: GraphClaimType = GraphClaimType.ASSERTION,
    review_state: GraphReviewState = GraphReviewState.CONFIRMED,
    valid_until: datetime | None = None,
    supersedes_record_key: str | None = None,
) -> GraphEdgeSnapshot:
    return GraphEdgeSnapshot(
        edge_key="relationship:acme:provider",
        source_node_key="organization:provider",
        target_node_key="organization:acme",
        edge_type=GraphEdgeType.PROVIDES_TO,
        source_module="relationship_intelligence",
        source_record_key=source_record_key,
        source_evidence_class=evidence_class,
        claim_type=claim_type,
        review_state=review_state,
        observed_at=observed_at,
        valid_until=valid_until,
        confidence=0.9,
        supersedes_record_key=supersedes_record_key,
    )

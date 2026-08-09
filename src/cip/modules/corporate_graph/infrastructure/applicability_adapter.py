from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.corporate_graph.application.batches import GraphProjectionBatch
from cip.modules.corporate_graph.domain.models import (
    GraphClaimType,
    GraphEdgeSnapshot,
    GraphEdgeType,
    GraphNodeSnapshot,
    GraphNodeType,
    GraphReviewState,
)
from cip.modules.vulnerability_applicability.infrastructure.models import (
    ApplicabilityAssessmentSnapshotRecord,
    VendorProductRecord,
)
from cip.modules.vulnerability_knowledge.infrastructure.models import VulnerabilityRecord

_TERMINAL_STATES = {"not_applicable", "withdrawn", "superseded"}


def load_applicability_graph(session: Session) -> GraphProjectionBatch:
    products = tuple(session.scalars(select(VendorProductRecord)).all())
    vulnerabilities = tuple(session.scalars(select(VulnerabilityRecord)).all())
    assessments = tuple(session.scalars(select(ApplicabilityAssessmentSnapshotRecord)).all())
    nodes: list[GraphNodeSnapshot] = []
    edges: list[GraphEdgeSnapshot] = []
    for product in products:
        nodes.append(_product_node(product))
    for vulnerability in vulnerabilities:
        nodes.append(_vulnerability_node(vulnerability))
    grouped: dict[str, list[ApplicabilityAssessmentSnapshotRecord]] = defaultdict(list)
    for assessment in assessments:
        grouped[assessment.identity_key].append(assessment)
    for identity_assessments in grouped.values():
        previous_key: str | None = None
        for assessment in sorted(identity_assessments, key=lambda item: item.assessed_at):
            record_key = _assessment_record_key(assessment)
            edges.append(_applicability_edge(assessment, previous_key=previous_key))
            product_edge = _product_usage_edge(assessment, previous_key=previous_key)
            if product_edge is not None:
                edges.append(product_edge)
            previous_key = record_key
    return GraphProjectionBatch(nodes=tuple(nodes), edges=tuple(edges))


def _product_node(record: VendorProductRecord) -> GraphNodeSnapshot:
    component = f" / {record.component}" if record.component else ""
    return GraphNodeSnapshot(
        node_key=f"product:{record.product_key}",
        node_type=GraphNodeType.PRODUCT,
        display_name=f"{record.vendor} {record.product}{component}",
        source_module="vulnerability_applicability",
        source_entity_type="vendor_product",
        source_record_key=record.product_key,
        source_entity_id=record.id,
        observed_at=record.updated_at,
        confidence=1.0,
        active=True,
    )


def _vulnerability_node(record: VulnerabilityRecord) -> GraphNodeSnapshot:
    return GraphNodeSnapshot(
        node_key=f"vulnerability:{record.id}",
        node_type=GraphNodeType.VULNERABILITY,
        display_name=record.canonical_id,
        source_module="vulnerability_knowledge",
        source_entity_type="vulnerability",
        source_record_key=record.canonical_id,
        source_entity_id=record.id,
        observed_at=record.updated_at,
        valid_from=record.published_at,
        confidence=1.0,
        active=record.status not in {"withdrawn", "rejected"},
    )


def _applicability_edge(
    record: ApplicabilityAssessmentSnapshotRecord,
    *,
    previous_key: str | None,
) -> GraphEdgeSnapshot:
    terminal = record.state in _TERMINAL_STATES
    return GraphEdgeSnapshot(
        edge_key=f"applicability:{record.identity_key}",
        source_node_key=f"vulnerability:{record.vulnerability_id}",
        target_node_key=f"asset:{record.asset_id}",
        edge_type=GraphEdgeType.VULNERABILITY_APPLIES_TO,
        source_module="vulnerability_applicability",
        source_record_key=_assessment_record_key(record),
        source_evidence_class=f"applicability:{record.state}:{record.precision}",
        claim_type=GraphClaimType.RETRACTION if terminal else GraphClaimType.ASSERTION,
        review_state=_review_state(record.state),
        observed_at=record.assessed_at,
        confidence=record.confidence,
        active=not terminal,
        supersedes_record_key=previous_key,
    )


def _product_usage_edge(
    record: ApplicabilityAssessmentSnapshotRecord,
    *,
    previous_key: str | None,
) -> GraphEdgeSnapshot | None:
    if record.matched_product_key is None:
        return None
    terminal = record.state in _TERMINAL_STATES
    suffix = ":product"
    return GraphEdgeSnapshot(
        edge_key=f"asset-product:{record.asset_id}:{record.matched_product_key}",
        source_node_key=f"asset:{record.asset_id}",
        target_node_key=f"product:{record.matched_product_key}",
        edge_type=GraphEdgeType.USES_PRODUCT,
        source_module="vulnerability_applicability",
        source_record_key=f"{_assessment_record_key(record)}{suffix}",
        source_evidence_class=f"product_match:{record.precision}",
        claim_type=GraphClaimType.RETRACTION if terminal else GraphClaimType.ASSERTION,
        review_state=_review_state(record.state),
        observed_at=record.assessed_at,
        confidence=record.confidence,
        active=not terminal,
        supersedes_record_key=f"{previous_key}{suffix}" if previous_key else None,
    )


def _assessment_record_key(record: ApplicabilityAssessmentSnapshotRecord) -> str:
    return f"assessment:{record.identity_key}:{record.snapshot_key}"


def _review_state(state: str) -> GraphReviewState:
    if state == "applicable":
        return GraphReviewState.CONFIRMED
    if state in {"review_required", "potentially_applicable", "unknown"}:
        return GraphReviewState.REVIEW_REQUIRED
    if state in _TERMINAL_STATES:
        return GraphReviewState.REJECTED
    return GraphReviewState.UNREVIEWED

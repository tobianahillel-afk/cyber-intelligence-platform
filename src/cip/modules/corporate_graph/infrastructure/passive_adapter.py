from __future__ import annotations

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
from cip.modules.passive_exposure.infrastructure.models import (
    PassiveObservationSnapshotRecord,
    PassiveTechnologyRecord,
)


def load_passive_graph(session: Session) -> GraphProjectionBatch:
    observations = tuple(session.scalars(select(PassiveObservationSnapshotRecord)).all())
    technologies = tuple(
        session.execute(
            select(PassiveTechnologyRecord, PassiveObservationSnapshotRecord).join(
                PassiveObservationSnapshotRecord,
                PassiveTechnologyRecord.snapshot_id == PassiveObservationSnapshotRecord.id,
            )
        ).all()
    )
    nodes: list[GraphNodeSnapshot] = []
    edges: list[GraphEdgeSnapshot] = []
    for observation in observations:
        nodes.append(_asset_node(observation))
        attribution = _attribution_edge(observation)
        if attribution is not None:
            edges.append(attribution)
    for technology, observation in technologies:
        nodes.append(_technology_node(technology, observation))
        edges.append(_technology_edge(technology, observation))
    return GraphProjectionBatch(nodes=tuple(nodes), edges=tuple(edges))


def _asset_node(record: PassiveObservationSnapshotRecord) -> GraphNodeSnapshot:
    organization_id = record.organization_id if record.organization_link_status == "exact" else None
    return GraphNodeSnapshot(
        node_key=f"asset:{record.asset_id}",
        node_type=_asset_node_type(record.asset_kind),
        display_name=record.asset_value,
        source_module="passive_exposure",
        source_entity_type=record.asset_kind,
        source_record_key=record.source_record_key,
        source_entity_id=record.asset_id,
        organization_id=organization_id,
        source_url=record.source_url,
        observed_at=record.observed_at,
        valid_until=record.expires_at,
        confidence=record.confidence,
        active=record.active and not record.historical_only,
        metadata_only=record.metadata_only,
    )


def _attribution_edge(
    record: PassiveObservationSnapshotRecord,
) -> GraphEdgeSnapshot | None:
    if record.organization_id is None or record.organization_link_status != "exact":
        return None
    edge_type = (
        GraphEdgeType.USES_DOMAIN
        if record.asset_kind in {"domain", "hostname"}
        else GraphEdgeType.OWNS_ASSET
    )
    return GraphEdgeSnapshot(
        edge_key=f"passive-attribution:{record.organization_id}:{record.asset_id}",
        source_node_key=f"organization:{record.organization_id}",
        target_node_key=f"asset:{record.asset_id}",
        edge_type=edge_type,
        source_module="passive_exposure",
        source_record_key=record.source_record_key,
        source_evidence_class="passive_attribution",
        claim_type=GraphClaimType.ASSERTION,
        review_state=GraphReviewState.CONFIRMED,
        source_url=record.source_url,
        observed_at=record.observed_at,
        valid_until=record.expires_at,
        expires_at=record.expires_at,
        confidence=min(record.confidence, record.organization_link_confidence),
        active=record.active and not record.historical_only,
        supersedes_record_key=record.supersedes_record_key,
    )


def _technology_node(
    technology: PassiveTechnologyRecord,
    observation: PassiveObservationSnapshotRecord,
) -> GraphNodeSnapshot:
    display_name = technology.product_name or technology.component_name or technology.technology_key
    if technology.product_version:
        display_name = f"{display_name} {technology.product_version}"
    return GraphNodeSnapshot(
        node_key=f"technology:{technology.technology_key}",
        node_type=GraphNodeType.TECHNOLOGY,
        display_name=display_name,
        source_module="passive_exposure",
        source_entity_type="technology",
        source_record_key=f"{observation.source_record_key}:{technology.technology_key}",
        source_entity_id=technology.id,
        organization_id=(
            observation.organization_id
            if observation.organization_link_status == "exact"
            else None
        ),
        source_url=observation.source_url,
        observed_at=observation.observed_at,
        valid_until=observation.expires_at,
        confidence=observation.confidence,
        active=observation.active and not observation.historical_only,
        metadata_only=observation.metadata_only,
    )


def _technology_edge(
    technology: PassiveTechnologyRecord,
    observation: PassiveObservationSnapshotRecord,
) -> GraphEdgeSnapshot:
    return GraphEdgeSnapshot(
        edge_key=f"asset-technology:{observation.asset_id}:{technology.technology_key}",
        source_node_key=f"asset:{observation.asset_id}",
        target_node_key=f"technology:{technology.technology_key}",
        edge_type=GraphEdgeType.USES_TECHNOLOGY,
        source_module="passive_exposure",
        source_record_key=f"{observation.source_record_key}:{technology.technology_key}",
        source_evidence_class=technology.evidence_level,
        claim_type=GraphClaimType.ASSERTION,
        review_state=GraphReviewState.UNREVIEWED,
        source_url=observation.source_url,
        observed_at=observation.observed_at,
        valid_until=observation.expires_at,
        expires_at=observation.expires_at,
        confidence=observation.confidence,
        active=observation.active and not observation.historical_only,
        supersedes_record_key=(
            f"{observation.supersedes_record_key}:{technology.technology_key}"
            if observation.supersedes_record_key
            else None
        ),
    )


def _asset_node_type(asset_kind: str) -> GraphNodeType:
    if asset_kind in {"domain", "hostname"}:
        return GraphNodeType.DOMAIN
    return GraphNodeType.ASSET

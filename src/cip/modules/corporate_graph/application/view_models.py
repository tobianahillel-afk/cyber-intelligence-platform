from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from cip.modules.corporate_graph.domain.blast_radius import BlastRadiusPreview


@dataclass(frozen=True, slots=True)
class GraphNodeFilters:
    node_type: str | None = None
    organization_id: UUID | None = None
    current: bool | None = None
    suppressed: bool | None = None
    query: str | None = None


@dataclass(frozen=True, slots=True)
class GraphNodeSummary:
    id: UUID
    node_key: str
    node_type: str
    display_name: str
    organization_id: UUID | None
    source_count: int
    confidence: float
    current: bool
    suppressed: bool
    first_observed_at: datetime
    last_observed_at: datetime


@dataclass(frozen=True, slots=True)
class GraphEdgeSummary:
    id: UUID
    edge_key: str
    source_node_key: str
    target_node_key: str
    edge_type: str
    source_module: str
    source_evidence_class: str
    review_state: str
    confidence: float
    current: bool
    suppressed: bool
    valid_from: datetime | None
    valid_until: datetime | None
    first_observed_at: datetime
    last_observed_at: datetime


@dataclass(frozen=True, slots=True)
class GraphNodeSnapshotView:
    id: UUID
    snapshot_key: str
    source_module: str
    source_entity_type: str
    source_record_key: str
    source_url: str | None
    organization_id: UUID | None
    observed_at: datetime
    valid_from: datetime | None
    valid_until: datetime | None
    confidence: float
    active: bool
    suppressed: bool


@dataclass(frozen=True, slots=True)
class GraphNodeDetail:
    node: GraphNodeSummary
    snapshots: tuple[GraphNodeSnapshotView, ...]
    outgoing_edges: tuple[GraphEdgeSummary, ...]
    incoming_edges: tuple[GraphEdgeSummary, ...]
    as_of: datetime | None = None


@dataclass(frozen=True, slots=True)
class GraphNodePage:
    items: tuple[GraphNodeSummary, ...]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class ResolutionCandidateSummary:
    id: UUID
    node_key: str
    candidate_organization_id: UUID
    method: str
    score: float
    reasons: tuple[str, ...]
    conflicting_organization_ids: tuple[UUID, ...]
    state: str
    requires_review: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ResolutionDecisionSummary:
    id: UUID
    candidate_id: UUID
    node_key: str
    decision_type: str
    actor: str
    reason: str
    organization_id: UUID | None
    reverses_decision_id: UUID | None
    blast_radius_fingerprint: str
    decided_at: datetime


@dataclass(frozen=True, slots=True)
class ResolutionCandidateDetail:
    candidate: ResolutionCandidateSummary
    decisions: tuple[ResolutionDecisionSummary, ...]
    blast_radius: BlastRadiusPreview


@dataclass(frozen=True, slots=True)
class ResolutionCandidatePage:
    items: tuple[ResolutionCandidateSummary, ...]
    total: int
    limit: int
    offset: int

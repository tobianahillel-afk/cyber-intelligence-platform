from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from cip.modules.corporate_graph.application.view_models import (
    GraphEdgeSummary,
    GraphNodeDetail,
    GraphNodePage,
    GraphNodeSnapshotView,
    GraphNodeSummary,
    ResolutionCandidateDetail,
    ResolutionCandidatePage,
    ResolutionCandidateSummary,
    ResolutionDecisionSummary,
)
from cip.modules.corporate_graph.domain.blast_radius import BlastRadiusPreview
from cip.modules.corporate_graph.domain.resolution import ResolutionDecisionType


class GraphNodeSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    node_key: str
    node_type: str
    display_name: str
    organization_id: UUID | None
    source_count: int = Field(ge=1)
    confidence: float = Field(ge=0, le=1)
    current: bool
    suppressed: bool
    first_observed_at: datetime
    last_observed_at: datetime

    @classmethod
    def from_domain(cls, item: GraphNodeSummary) -> GraphNodeSummaryResponse:
        return cls(**asdict(item))


class GraphEdgeSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    edge_key: str
    source_node_key: str
    target_node_key: str
    edge_type: str
    source_module: str
    source_evidence_class: str
    review_state: str
    confidence: float = Field(ge=0, le=1)
    current: bool
    suppressed: bool
    valid_from: datetime | None
    valid_until: datetime | None
    first_observed_at: datetime
    last_observed_at: datetime

    @classmethod
    def from_domain(cls, item: GraphEdgeSummary) -> GraphEdgeSummaryResponse:
        return cls(**asdict(item))


class GraphNodeSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    confidence: float = Field(ge=0, le=1)
    active: bool
    suppressed: bool

    @classmethod
    def from_domain(cls, item: GraphNodeSnapshotView) -> GraphNodeSnapshotResponse:
        return cls(**asdict(item))


class GraphNodePageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[GraphNodeSummaryResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)

    @classmethod
    def from_domain(cls, page: GraphNodePage) -> GraphNodePageResponse:
        return cls(
            items=[GraphNodeSummaryResponse.from_domain(item) for item in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )


class GraphNodeDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node: GraphNodeSummaryResponse
    snapshots: list[GraphNodeSnapshotResponse]
    outgoing_edges: list[GraphEdgeSummaryResponse]
    incoming_edges: list[GraphEdgeSummaryResponse]
    as_of: datetime | None
    evidence_disclaimer: str

    @classmethod
    def from_domain(cls, detail: GraphNodeDetail) -> GraphNodeDetailResponse:
        return cls(
            node=GraphNodeSummaryResponse.from_domain(detail.node),
            snapshots=[GraphNodeSnapshotResponse.from_domain(item) for item in detail.snapshots],
            outgoing_edges=[
                GraphEdgeSummaryResponse.from_domain(item) for item in detail.outgoing_edges
            ],
            incoming_edges=[
                GraphEdgeSummaryResponse.from_domain(item) for item in detail.incoming_edges
            ],
            as_of=detail.as_of,
            evidence_disclaimer=(
                "Graph membership preserves source lineage, evidence class, review state, "
                "and temporal validity. Claimed, inferred, historical, disputed, or "
                "retracted edges are never upgraded into verified current facts."
            ),
        )


class ResolutionCandidateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    node_key: str
    candidate_organization_id: UUID
    method: str
    score: float = Field(ge=0, le=1)
    reasons: list[str]
    conflicting_organization_ids: list[UUID]
    state: str
    requires_review: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, item: ResolutionCandidateSummary) -> ResolutionCandidateResponse:
        values = asdict(item)
        values["reasons"] = list(item.reasons)
        values["conflicting_organization_ids"] = list(item.conflicting_organization_ids)
        return cls(**values)


class ResolutionDecisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

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

    @classmethod
    def from_domain(cls, item: ResolutionDecisionSummary) -> ResolutionDecisionResponse:
        return cls(**asdict(item))


class BlastRadiusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_key: str
    target_organization_key: str | None
    resolution_state_key: str
    graph_nodes: int = Field(ge=0)
    graph_edges: int = Field(ge=0)
    organization_identities: int = Field(ge=0)
    business_relationships: int = Field(ge=0)
    applicability_assessments: int = Field(ge=0)
    commercial_signals: int = Field(ge=0)
    opportunities: int = Field(ge=0)
    downstream_record_count: int = Field(ge=0)
    requires_explicit_confirmation: bool
    fingerprint: str

    @classmethod
    def from_domain(cls, item: BlastRadiusPreview) -> BlastRadiusResponse:
        values = asdict(item)
        values["downstream_record_count"] = item.downstream_record_count
        values["requires_explicit_confirmation"] = item.requires_explicit_confirmation
        values["fingerprint"] = item.fingerprint
        return cls(**values)


class ResolutionCandidatePageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ResolutionCandidateResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)

    @classmethod
    def from_domain(cls, page: ResolutionCandidatePage) -> ResolutionCandidatePageResponse:
        return cls(
            items=[ResolutionCandidateResponse.from_domain(item) for item in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )


class ResolutionCandidateDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate: ResolutionCandidateResponse
    decisions: list[ResolutionDecisionResponse]
    blast_radius: BlastRadiusResponse

    @classmethod
    def from_domain(
        cls,
        detail: ResolutionCandidateDetail,
    ) -> ResolutionCandidateDetailResponse:
        return cls(
            candidate=ResolutionCandidateResponse.from_domain(detail.candidate),
            decisions=[ResolutionDecisionResponse.from_domain(item) for item in detail.decisions],
            blast_radius=BlastRadiusResponse.from_domain(detail.blast_radius),
        )


class ResolutionDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_type: ResolutionDecisionType
    actor: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=1_000)
    organization_id: UUID | None = None
    reverses_decision_id: UUID | None = None
    blast_radius_fingerprint: str = Field(min_length=64, max_length=64)


class GraphRefreshResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    node_snapshot_count: int = Field(ge=0)
    edge_snapshot_count: int = Field(ge=0)
    candidate_count: int = Field(ge=0)

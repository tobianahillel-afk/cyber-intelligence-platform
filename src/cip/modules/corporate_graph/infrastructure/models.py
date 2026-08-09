from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base
from cip.shared.persistence.types import UTCDateTime


class CorporateGraphNodeRecord(Base):
    __tablename__ = "corporate_graph_nodes"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    node_key: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    node_type: Mapped[str] = mapped_column(String(80), index=True)
    display_name: Mapped[str] = mapped_column(String(500), index=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_count: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    current: Mapped[bool] = mapped_column(Boolean, index=True)
    suppressed: Mapped[bool] = mapped_column(Boolean, index=True)
    first_observed_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    last_observed_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)


class CorporateGraphNodeSnapshotRecord(Base):
    __tablename__ = "corporate_graph_node_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_key", name="uq_corporate_graph_node_snapshot"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    node_id: Mapped[UUID] = mapped_column(
        ForeignKey("corporate_graph_nodes.id", ondelete="CASCADE"),
        index=True,
    )
    snapshot_key: Mapped[str] = mapped_column(String(64), unique=True)
    node_key: Mapped[str] = mapped_column(String(500), index=True)
    node_type: Mapped[str] = mapped_column(String(80), index=True)
    display_name: Mapped[str] = mapped_column(String(500), index=True)
    source_module: Mapped[str] = mapped_column(String(100), index=True)
    source_entity_type: Mapped[str] = mapped_column(String(100), index=True)
    source_record_key: Mapped[str] = mapped_column(String(500), index=True)
    source_entity_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_url: Mapped[str | None] = mapped_column(String(2_048), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    valid_from: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True, index=True)
    valid_until: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True, index=True)
    confidence: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, index=True)
    suppressed: Mapped[bool] = mapped_column(Boolean, index=True)
    metadata_only: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())


class CorporateGraphEdgeRecord(Base):
    __tablename__ = "corporate_graph_edges"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    edge_key: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    source_node_key: Mapped[str] = mapped_column(
        ForeignKey("corporate_graph_nodes.node_key", ondelete="CASCADE"),
        index=True,
    )
    target_node_key: Mapped[str] = mapped_column(
        ForeignKey("corporate_graph_nodes.node_key", ondelete="CASCADE"),
        index=True,
    )
    edge_type: Mapped[str] = mapped_column(String(80), index=True)
    source_module: Mapped[str] = mapped_column(String(100), index=True)
    source_evidence_class: Mapped[str] = mapped_column(String(100), index=True)
    review_state: Mapped[str] = mapped_column(String(80), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    current: Mapped[bool] = mapped_column(Boolean, index=True)
    suppressed: Mapped[bool] = mapped_column(Boolean, index=True)
    valid_from: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True, index=True)
    valid_until: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True, index=True)
    first_observed_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    last_observed_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)


class CorporateGraphEdgeSnapshotRecord(Base):
    __tablename__ = "corporate_graph_edge_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_key", name="uq_corporate_graph_edge_snapshot"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    edge_id: Mapped[UUID] = mapped_column(
        ForeignKey("corporate_graph_edges.id", ondelete="CASCADE"),
        index=True,
    )
    snapshot_key: Mapped[str] = mapped_column(String(64), unique=True)
    edge_key: Mapped[str] = mapped_column(String(500), index=True)
    source_node_key: Mapped[str] = mapped_column(String(500), index=True)
    target_node_key: Mapped[str] = mapped_column(String(500), index=True)
    edge_type: Mapped[str] = mapped_column(String(80), index=True)
    source_module: Mapped[str] = mapped_column(String(100), index=True)
    source_record_key: Mapped[str] = mapped_column(String(500), index=True)
    source_evidence_class: Mapped[str] = mapped_column(String(100), index=True)
    claim_type: Mapped[str] = mapped_column(String(80), index=True)
    review_state: Mapped[str] = mapped_column(String(80), index=True)
    source_url: Mapped[str | None] = mapped_column(String(2_048), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    valid_from: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True, index=True)
    valid_until: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True, index=True)
    confidence: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, index=True)
    suppressed: Mapped[bool] = mapped_column(Boolean, index=True)
    supersedes_record_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())


class EntityResolutionCandidateRecord(Base):
    __tablename__ = "entity_resolution_candidates"
    __table_args__ = (
        UniqueConstraint(
            "node_key",
            "candidate_organization_id",
            "method",
            name="uq_entity_resolution_candidate_identity",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    node_key: Mapped[str] = mapped_column(
        ForeignKey("corporate_graph_nodes.node_key", ondelete="CASCADE"),
        index=True,
    )
    candidate_organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )
    method: Mapped[str] = mapped_column(String(80), index=True)
    score: Mapped[float] = mapped_column(Float, index=True)
    reasons_json: Mapped[str] = mapped_column(Text)
    conflicting_organization_ids_json: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(80), index=True)
    requires_review: Mapped[bool] = mapped_column(Boolean, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)


class EntityResolutionDecisionRecord(Base):
    __tablename__ = "entity_resolution_decisions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("entity_resolution_candidates.id", ondelete="CASCADE"),
        index=True,
    )
    node_key: Mapped[str] = mapped_column(String(500), index=True)
    decision_type: Mapped[str] = mapped_column(String(80), index=True)
    actor: Mapped[str] = mapped_column(String(200), index=True)
    reason: Mapped[str] = mapped_column(String(1_000))
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reverses_decision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("entity_resolution_decisions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    blast_radius_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    decided_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())


class EntityResolutionBindingRecord(Base):
    __tablename__ = "entity_resolution_bindings"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    node_key: Mapped[str] = mapped_column(
        ForeignKey("corporate_graph_nodes.node_key", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )
    candidate_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("entity_resolution_candidates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    decision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("entity_resolution_decisions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    method: Mapped[str] = mapped_column(String(80), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    current: Mapped[bool] = mapped_column(Boolean, index=True)
    bound_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)

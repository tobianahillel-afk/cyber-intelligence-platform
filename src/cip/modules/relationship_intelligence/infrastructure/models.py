from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class BusinessRelationshipRecord(Base):
    __tablename__ = "business_relationships"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    relationship_key: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(80), index=True)
    source_organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    target_organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_link_status: Mapped[str] = mapped_column(String(80), index=True)
    target_link_status: Mapped[str] = mapped_column(String(80), index=True)
    source_name: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    target_name: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    first_published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    evidence_count: Mapped[int] = mapped_column(Integer)
    independent_source_count: Mapped[int] = mapped_column(Integer)
    strongest_evidence_class: Mapped[str] = mapped_column(String(40), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    has_contract_evidence: Mapped[bool] = mapped_column(Boolean, index=True)
    contract_backed_current: Mapped[bool] = mapped_column(Boolean, index=True)
    next_renewal_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    has_role_conflict: Mapped[bool] = mapped_column(Boolean, index=True)
    has_dispute: Mapped[bool] = mapped_column(Boolean, index=True)
    has_correction: Mapped[bool] = mapped_column(Boolean, index=True)
    has_retraction: Mapped[bool] = mapped_column(Boolean, index=True)
    historical_only: Mapped[bool] = mapped_column(Boolean, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class RelationshipEvidenceSnapshotRecord(Base):
    __tablename__ = "relationship_evidence_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_key", name="uq_relationship_evidence_snapshot"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    relationship_id: Mapped[UUID] = mapped_column(
        ForeignKey("business_relationships.id", ondelete="CASCADE"), index=True
    )
    snapshot_key: Mapped[str] = mapped_column(String(64))
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    source_kind: Mapped[str] = mapped_column(String(80), index=True)
    source_record_key: Mapped[str] = mapped_column(String(500), index=True)
    source_url: Mapped[str] = mapped_column(String(2_048))
    relationship_key: Mapped[str] = mapped_column(String(500), index=True)
    claim_type: Mapped[str] = mapped_column(String(80), index=True)
    role: Mapped[str] = mapped_column(String(80), index=True)
    evidence_class: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(1_000))
    excerpt: Mapped[str] = mapped_column(String(500))
    claimed_source_organization_name: Mapped[str | None] = mapped_column(
        String(500), nullable=True, index=True
    )
    claimed_target_organization_name: Mapped[str | None] = mapped_column(
        String(500), nullable=True, index=True
    )
    source_organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    target_organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_link_status: Mapped[str] = mapped_column(String(80), index=True)
    target_link_status: Mapped[str] = mapped_column(String(80), index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    modified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    contract_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    product_context: Mapped[str | None] = mapped_column(String(500), nullable=True)
    service_context: Mapped[str | None] = mapped_column(String(500), nullable=True)
    renewal_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    independence_key: Mapped[str] = mapped_column(String(500), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, index=True)
    historical_only: Mapped[bool] = mapped_column(Boolean, index=True)
    metadata_only: Mapped[bool] = mapped_column(Boolean)
    supersedes_record_key: Mapped[str | None] = mapped_column(
        String(500), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RelationshipContextRecord(Base):
    __tablename__ = "relationship_contexts"
    __table_args__ = (
        UniqueConstraint(
            "relationship_id",
            "context_type",
            "value",
            name="uq_relationship_context_value",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    relationship_id: Mapped[UUID] = mapped_column(
        ForeignKey("business_relationships.id", ondelete="CASCADE"), index=True
    )
    context_type: Mapped[str] = mapped_column(String(40), index=True)
    value: Mapped[str] = mapped_column(String(500), index=True)
    reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    confidence: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

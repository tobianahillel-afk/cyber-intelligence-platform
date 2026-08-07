from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class CorporateChangeEventRecord(Base):
    __tablename__ = "corporate_change_events"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    event_key: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(1_000))
    excerpt: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(80), index=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    organization_link_status: Mapped[str] = mapped_column(String(80), index=True)
    event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    first_published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    claim_count: Mapped[int] = mapped_column(Integer)
    independent_source_count: Mapped[int] = mapped_column(Integer)
    officially_confirmed: Mapped[bool] = mapped_column(Boolean, index=True)
    has_dispute: Mapped[bool] = mapped_column(Boolean, index=True)
    has_correction: Mapped[bool] = mapped_column(Boolean, index=True)
    has_retraction: Mapped[bool] = mapped_column(Boolean, index=True)
    historical_only: Mapped[bool] = mapped_column(Boolean, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class CorporateChangeClaimSnapshotRecord(Base):
    __tablename__ = "corporate_change_claim_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_key", name="uq_corporate_change_claim_snapshot"),
        Index("ix_change_claim_source_record", "source_id", "source_record_key"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("corporate_change_events.id", ondelete="CASCADE"), index=True
    )
    snapshot_key: Mapped[str] = mapped_column(String(64))
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    source_kind: Mapped[str] = mapped_column(String(80), index=True)
    source_record_key: Mapped[str] = mapped_column(String(500), index=True)
    article_id: Mapped[str] = mapped_column(String(500), index=True)
    source_url: Mapped[str] = mapped_column(String(2_048))
    event_key: Mapped[str] = mapped_column(String(500), index=True)
    claim_type: Mapped[str] = mapped_column(String(80), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(1_000))
    excerpt: Mapped[str] = mapped_column(String(500))
    claimed_organization_name: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    organization_link_status: Mapped[str] = mapped_column(String(80), index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    modified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    independence_key: Mapped[str] = mapped_column(String(500), index=True)
    syndication_group_key: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    confidence: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, index=True)
    historical_only: Mapped[bool] = mapped_column(Boolean, index=True)
    metadata_only: Mapped[bool] = mapped_column(Boolean)
    supersedes_record_key: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CorporateChangeServiceMappingRecord(Base):
    __tablename__ = "corporate_change_service_mappings"
    __table_args__ = (
        UniqueConstraint("event_id", "service_family", name="uq_change_event_service_family"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("corporate_change_events.id", ondelete="CASCADE"), index=True
    )
    service_family: Mapped[str] = mapped_column(String(120), index=True)
    rationale: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

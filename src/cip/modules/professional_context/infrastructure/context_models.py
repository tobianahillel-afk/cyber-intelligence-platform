from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class ProfessionalCommunityRecord(Base):
    __tablename__ = "professional_community_contexts"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    context_key: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    community_name: Mapped[str] = mapped_column(String(300), index=True)
    context_type: Mapped[str] = mapped_column(String(100), index=True)
    context_value: Mapped[str] = mapped_column(String(500))
    acquisition_mode: Mapped[str] = mapped_column(String(50), index=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    person_key: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    confidence: Mapped[float] = mapped_column(Float)
    review_state: Mapped[str] = mapped_column(String(32), index=True)
    lawful_basis: Mapped[str] = mapped_column(String(40), index=True)
    lawful_basis_reference: Mapped[str] = mapped_column(String(500))
    processing_purpose: Mapped[str] = mapped_column(String(300), index=True)
    current: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    suppressed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    retention_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ProfessionalCommunitySnapshotRecord(Base):
    __tablename__ = "professional_community_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    context_id: Mapped[UUID] = mapped_column(
        ForeignKey("professional_community_contexts.id", ondelete="CASCADE"), index=True
    )
    snapshot_key: Mapped[str] = mapped_column(String(64), unique=True)
    context_key: Mapped[str] = mapped_column(String(500), index=True)
    community_name: Mapped[str] = mapped_column(String(300), index=True)
    context_type: Mapped[str] = mapped_column(String(100), index=True)
    context_value: Mapped[str] = mapped_column(String(500))
    acquisition_mode: Mapped[str] = mapped_column(String(50), index=True)
    authorization_reference: Mapped[str] = mapped_column(String(500))
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    person_key: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    source_record_key: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(String(2_048), nullable=True)
    claim_type: Mapped[str] = mapped_column(String(32), index=True)
    review_state: Mapped[str] = mapped_column(String(32), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    suppressed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    metadata_only: Mapped[bool] = mapped_column(Boolean, default=True)
    supersedes_record_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    lawful_basis: Mapped[str] = mapped_column(String(40), index=True)
    lawful_basis_reference: Mapped[str] = mapped_column(String(500))
    processing_purpose: Mapped[str] = mapped_column(String(300), index=True)
    processing_reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    retention_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProfessionalServiceRelevanceRecord(Base):
    __tablename__ = "professional_service_relevance"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    mapping_key: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    person_key: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    service_family: Mapped[str] = mapped_column(String(80), index=True)
    rationale: Mapped[str] = mapped_column(String(500))
    confidence: Mapped[float] = mapped_column(Float)
    source_claim_keys: Mapped[list[str]] = mapped_column(JSON, default=list)
    review_state: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

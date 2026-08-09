from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class ProfessionalContactRecord(Base):
    __tablename__ = "professional_contacts"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    contact_key: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    channel_type: Mapped[str] = mapped_column(String(40), index=True)
    value: Mapped[str | None] = mapped_column(String(2_048), nullable=True)
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


class ProfessionalContactSnapshotRecord(Base):
    __tablename__ = "professional_contact_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    contact_id: Mapped[UUID] = mapped_column(
        ForeignKey("professional_contacts.id", ondelete="CASCADE"), index=True
    )
    snapshot_key: Mapped[str] = mapped_column(String(64), unique=True)
    contact_key: Mapped[str] = mapped_column(String(500), index=True)
    channel_type: Mapped[str] = mapped_column(String(40), index=True)
    evidence_scope: Mapped[str] = mapped_column(String(40), index=True)
    value: Mapped[str | None] = mapped_column(String(2_048), nullable=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    person_key: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    source_record_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2_048), nullable=True)
    claim_type: Mapped[str] = mapped_column(String(32), index=True)
    review_state: Mapped[str] = mapped_column(String(32), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    suppressed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    supersedes_record_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    lawful_basis: Mapped[str] = mapped_column(String(40), index=True)
    lawful_basis_reference: Mapped[str] = mapped_column(String(500))
    processing_purpose: Mapped[str] = mapped_column(String(300), index=True)
    processing_reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    retention_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

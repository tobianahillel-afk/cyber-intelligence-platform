from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class ProfessionalPersonRecord(Base):
    __tablename__ = "professional_people"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    person_key: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    review_state: Mapped[str] = mapped_column(String(32), index=True)
    lawful_basis: Mapped[str] = mapped_column(String(40), index=True)
    lawful_basis_reference: Mapped[str] = mapped_column(String(500))
    processing_purpose: Mapped[str] = mapped_column(String(300), index=True)
    current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    suppressed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    retention_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ProfessionalPersonSnapshotRecord(Base):
    __tablename__ = "professional_person_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("professional_people.id", ondelete="CASCADE"),
        index=True,
    )
    snapshot_key: Mapped[str] = mapped_column(String(64), unique=True)
    person_key: Mapped[str] = mapped_column(String(200), index=True)
    display_name: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    source_kind: Mapped[str] = mapped_column(String(80), index=True)
    source_record_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2_048), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    review_state: Mapped[str] = mapped_column(String(32), index=True)
    lawful_basis: Mapped[str] = mapped_column(String(40), index=True)
    lawful_basis_reference: Mapped[str] = mapped_column(String(500))
    processing_purpose: Mapped[str] = mapped_column(String(300), index=True)
    processing_reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    retention_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    suppressed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class ProfessionalRoleRecord(Base):
    __tablename__ = "professional_roles"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    claim_key: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    person_key: Mapped[str] = mapped_column(String(200), index=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    claimed_organization_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role_title: Mapped[str] = mapped_column(String(300), index=True)
    team_name: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    employment_state: Mapped[str] = mapped_column(String(32), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    review_state: Mapped[str] = mapped_column(String(32), index=True)
    lawful_basis: Mapped[str] = mapped_column(String(40), index=True)
    lawful_basis_reference: Mapped[str] = mapped_column(String(500))
    processing_purpose: Mapped[str] = mapped_column(String(300), index=True)
    suppressed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    evidence_count: Mapped[int] = mapped_column(Integer)
    first_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    retention_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ProfessionalRoleSnapshotRecord(Base):
    __tablename__ = "professional_role_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("professional_roles.id", ondelete="CASCADE"), index=True
    )
    snapshot_key: Mapped[str] = mapped_column(String(64), unique=True)
    claim_key: Mapped[str] = mapped_column(String(500), index=True)
    person_key: Mapped[str] = mapped_column(String(200), index=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    source_record_key: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(String(2_048), nullable=True)
    role_title: Mapped[str] = mapped_column(String(300), index=True)
    team_name: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    claimed_organization_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    organization_link_status: Mapped[str] = mapped_column(String(32), index=True)
    claim_type: Mapped[str] = mapped_column(String(32), index=True)
    review_state: Mapped[str] = mapped_column(String(32), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    historical_only: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    suppressed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    supersedes_record_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    lawful_basis: Mapped[str] = mapped_column(String(40), index=True)
    lawful_basis_reference: Mapped[str] = mapped_column(String(500))
    processing_purpose: Mapped[str] = mapped_column(String(300), index=True)
    processing_reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    retention_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProfessionalReportingLineRecord(Base):
    __tablename__ = "professional_reporting_lines"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    claim_key: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    subject_person_key: Mapped[str] = mapped_column(String(200), index=True)
    manager_person_key: Mapped[str] = mapped_column(String(200), index=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    confidence: Mapped[float] = mapped_column(Float)
    review_state: Mapped[str] = mapped_column(String(32), index=True)
    lawful_basis: Mapped[str] = mapped_column(String(40), index=True)
    lawful_basis_reference: Mapped[str] = mapped_column(String(500))
    processing_purpose: Mapped[str] = mapped_column(String(300), index=True)
    current: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    suppressed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    first_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    retention_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ProfessionalReportingSnapshotRecord(Base):
    __tablename__ = "professional_reporting_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    reporting_line_id: Mapped[UUID] = mapped_column(
        ForeignKey("professional_reporting_lines.id", ondelete="CASCADE"), index=True
    )
    snapshot_key: Mapped[str] = mapped_column(String(64), unique=True)
    claim_key: Mapped[str] = mapped_column(String(500), index=True)
    subject_person_key: Mapped[str] = mapped_column(String(200), index=True)
    manager_person_key: Mapped[str] = mapped_column(String(200), index=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    source_record_key: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(String(2_048), nullable=True)
    claim_type: Mapped[str] = mapped_column(String(32), index=True)
    review_state: Mapped[str] = mapped_column(String(32), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

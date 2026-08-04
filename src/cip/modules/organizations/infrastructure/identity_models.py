from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class OrganizationIdentityRecord(Base):
    __tablename__ = "organization_identities"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "source_record_key",
            name="uq_organization_identity_source_record",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=True,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(32), index=True)
    official_name: Mapped[str] = mapped_column(String(300), index=True)
    country_code: Mapped[str] = mapped_column(String(2), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    legal_form: Mapped[str | None] = mapped_column(String(300), nullable=True)
    activity_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    city: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    is_headquarters: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    source_id: Mapped[str] = mapped_column(String(100), index=True)
    source_record_key: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[str] = mapped_column(String(2_048))
    confidence: Mapped[float] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class OrganizationIdentifierRecord(Base):
    __tablename__ = "organization_identifiers"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    identity_id: Mapped[UUID] = mapped_column(
        ForeignKey("organization_identities.id", ondelete="CASCADE"),
        index=True,
    )
    scheme: Mapped[str] = mapped_column(String(32), index=True)
    value: Mapped[str] = mapped_column(String(100), index=True)
    issuing_country: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    exact_key: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    source_id: Mapped[str] = mapped_column(String(100), index=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class OrganizationAliasRecord(Base):
    __tablename__ = "organization_aliases"
    __table_args__ = (
        UniqueConstraint(
            "identity_id",
            "normalized_value",
            name="uq_organization_alias_identity_value",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    identity_id: Mapped[UUID] = mapped_column(
        ForeignKey("organization_identities.id", ondelete="CASCADE"),
        index=True,
    )
    value: Mapped[str] = mapped_column(String(300), index=True)
    normalized_value: Mapped[str] = mapped_column(String(300), index=True)
    source_id: Mapped[str] = mapped_column(String(100), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OrganizationRelationshipRecord(Base):
    __tablename__ = "organization_relationships"
    __table_args__ = (
        UniqueConstraint(
            "subject_identity_id",
            "object_identity_id",
            "relationship_type",
            "source_id",
            name="uq_organization_relationship_source",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    subject_identity_id: Mapped[UUID] = mapped_column(
        ForeignKey("organization_identities.id", ondelete="CASCADE"),
        index=True,
    )
    object_identity_id: Mapped[UUID] = mapped_column(
        ForeignKey("organization_identities.id", ondelete="CASCADE"),
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(String(40), index=True)
    source_id: Mapped[str] = mapped_column(String(100), index=True)
    source_url: Mapped[str] = mapped_column(String(2_048))
    confidence: Mapped[float] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)


class OrganizationMergeCandidateRecord(Base):
    __tablename__ = "organization_merge_candidates"
    __table_args__ = (
        UniqueConstraint(
            "identity_id",
            "organization_id",
            name="uq_organization_merge_candidate_pair",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    identity_id: Mapped[UUID] = mapped_column(
        ForeignKey("organization_identities.id", ondelete="CASCADE"),
        index=True,
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )
    method: Mapped[str] = mapped_column(String(50), index=True)
    score: Mapped[float] = mapped_column(Float, index=True)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    state: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class OrganizationIdentityEvidenceRecord(Base):
    __tablename__ = "organization_identity_evidence"

    identity_id: Mapped[UUID] = mapped_column(
        ForeignKey("organization_identities.id", ondelete="CASCADE"),
        primary_key=True,
    )
    evidence_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"),
        primary_key=True,
    )

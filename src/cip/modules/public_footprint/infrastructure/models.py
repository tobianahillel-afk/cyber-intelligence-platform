from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class PublicResourceRecord(Base):
    __tablename__ = "public_resources"
    __table_args__ = (
        UniqueConstraint("identity_key", name="uq_public_resource_identity"),
        Index(
            "ix_public_resource_source_record",
            "source_id",
            "source_record_key",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        index=True,
    )
    source_id: Mapped[str] = mapped_column(String(100), index=True)
    source_record_key: Mapped[str] = mapped_column(String(500), index=True)
    identity_key: Mapped[str] = mapped_column(String(64))
    corroboration_group_key: Mapped[str] = mapped_column(String(64), index=True)
    canonical_url: Mapped[str] = mapped_column(String(2_048), index=True)
    source_url: Mapped[str] = mapped_column(String(2_048))
    kind: Mapped[str] = mapped_column(String(40), index=True)
    discovery_method: Mapped[str] = mapped_column(String(40), index=True)
    access_state: Mapped[str] = mapped_column(String(40), index=True)
    retrieval_state: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str | None] = mapped_column(String(1_000), nullable=True)
    first_discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class PublicResourceVersionRecord(Base):
    __tablename__ = "public_resource_versions"
    __table_args__ = (
        UniqueConstraint("version_key", name="uq_public_resource_version"),
        Index(
            "ix_public_resource_version_resource_time",
            "resource_id",
            "fetched_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    resource_id: Mapped[UUID] = mapped_column(
        ForeignKey("public_resources.id", ondelete="CASCADE"),
        index=True,
    )
    version_key: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[str] = mapped_column(String(2_048))
    content_hash_sha256: Mapped[str] = mapped_column(String(64), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    mime_type: Mapped[str] = mapped_column(String(200), index=True)
    byte_size: Mapped[int] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(String(1_000), nullable=True)
    language: Mapped[str | None] = mapped_column(String(35), nullable=True, index=True)
    extracted_text_hash_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    excerpt: Mapped[str | None] = mapped_column(String(1_000), nullable=True)
    source_locator: Mapped[str | None] = mapped_column(String(500), nullable=True)
    supersedes_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("public_resource_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PublicClaimRecord(Base):
    __tablename__ = "public_claims"
    __table_args__ = (
        UniqueConstraint("claim_key", name="uq_public_claim_identity"),
        Index(
            "ix_public_claim_organization_type",
            "organization_id",
            "claim_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    claim_key: Mapped[str] = mapped_column(String(64))
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        index=True,
    )
    resource_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("public_resource_versions.id", ondelete="CASCADE"),
        index=True,
    )
    claim_type: Mapped[str] = mapped_column(String(80), index=True)
    statement: Mapped[str] = mapped_column(String(2_000))
    evidence_basis: Mapped[str] = mapped_column(String(80), index=True)
    resolution_status: Mapped[str] = mapped_column(String(40), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    corroboration_group_key: Mapped[str] = mapped_column(String(64), index=True)
    source_locator: Mapped[str | None] = mapped_column(String(500), nullable=True)
    excerpt: Mapped[str | None] = mapped_column(String(1_000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class PublicSurfaceReferenceRecord(Base):
    __tablename__ = "public_surface_references"
    __table_args__ = (
        UniqueConstraint("surface_key", name="uq_public_surface_identity"),
        Index(
            "ix_public_surface_organization_kind",
            "organization_id",
            "kind",
        ),
        Index(
            "ix_public_surface_version_kind",
            "resource_version_id",
            "kind",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    surface_key: Mapped[str] = mapped_column(String(64))
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        index=True,
    )
    resource_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("public_resource_versions.id", ondelete="CASCADE"),
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(40), index=True)
    source_locator: Mapped[str] = mapped_column(String(500))
    target_url: Mapped[str | None] = mapped_column(String(2_048), nullable=True)
    relation: Mapped[str | None] = mapped_column(String(200), nullable=True)
    http_method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    value: Mapped[str | None] = mapped_column(String(2_000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
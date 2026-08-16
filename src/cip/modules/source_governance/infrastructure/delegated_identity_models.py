from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class DelegatedBrowserIdentityRecord(Base):
    __tablename__ = "delegated_browser_identities"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "owner_kind",
            "owner_subject_id",
            "source_id",
            "purpose",
            "external_reference",
            name="uq_delegated_browser_identity_ownership",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"),
        index=True,
    )
    external_reference: Mapped[str] = mapped_column(String(500))
    auth_mode: Mapped[str] = mapped_column(String(40), index=True)
    account_status: Mapped[str] = mapped_column(String(40), index=True)
    authorization_document_reference: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    approved_purposes: Mapped[list[str]] = mapped_column(JSON)
    tenant_id: Mapped[UUID] = mapped_column(index=True)
    owner_kind: Mapped[str] = mapped_column(String(40), index=True)
    owner_subject_id: Mapped[str] = mapped_column(String(200), index=True)
    purpose: Mapped[str] = mapped_column(String(200), index=True)
    approved_scopes: Mapped[list[str]] = mapped_column(JSON)
    secret_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    session_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    account_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    renewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reference_rotated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    session_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    reference_version: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class DelegatedBrowserIdentityAuditRecord(Base):
    __tablename__ = "delegated_browser_identity_audit"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    identity_id: Mapped[UUID] = mapped_column(
        ForeignKey("delegated_browser_identities.id", ondelete="CASCADE"),
        index=True,
    )
    tenant_id: Mapped[UUID] = mapped_column(index=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    actor_kind: Mapped[str] = mapped_column(String(40))
    actor_subject_id: Mapped[str] = mapped_column(String(200))
    reference_version: Mapped[int] = mapped_column(Integer)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

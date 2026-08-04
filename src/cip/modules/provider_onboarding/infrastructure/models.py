from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class ProviderOnboardingRecord(Base):
    __tablename__ = "provider_onboarding"

    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        primary_key=True,
    )
    display_name: Mapped[str] = mapped_column(String(200))
    auth_mode: Mapped[str] = mapped_column(String(40), index=True)
    state: Mapped[str] = mapped_column(String(50), index=True)
    documentation_url: Mapped[str] = mapped_column(String(2_048))
    signup_url: Mapped[str | None] = mapped_column(String(2_048), nullable=True)
    console_url: Mapped[str | None] = mapped_column(String(2_048), nullable=True)
    required_secret_names: Mapped[list[str]] = mapped_column(JSON, default=list)
    human_actions: Mapped[list[str]] = mapped_column(JSON, default=list)
    automatic_onboarding: Mapped[bool]
    secret_references: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ProviderOnboardingAuditRecord(Base):
    __tablename__ = "provider_onboarding_audit"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), index=True)
    previous_state: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_state: Mapped[str] = mapped_column(String(50), index=True)
    actor: Mapped[str] = mapped_column(String(200))
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class BrowserEvidenceArtifactRecord(Base):
    __tablename__ = "browser_evidence_artifacts"
    __table_args__ = (
        UniqueConstraint("artifact_key", name="uq_browser_evidence_artifact_identity"),
        ForeignKeyConstraint(
            ["plan_id", "plan_version"],
            ["browser_action_plans.plan_id", "browser_action_plans.plan_version"],
            ondelete="CASCADE",
        ),
        Index(
            "ix_browser_evidence_artifacts_source_kind",
            "source_id",
            "kind",
        ),
        Index(
            "ix_browser_evidence_artifacts_plan",
            "plan_id",
            "plan_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    artifact_key: Mapped[str] = mapped_column(String(64))
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    provider_id: Mapped[str] = mapped_column(String(200), index=True)
    target_id: Mapped[str] = mapped_column(String(200), index=True)
    job_id: Mapped[UUID] = mapped_column(index=True)
    plan_id: Mapped[UUID] = mapped_column()
    plan_version: Mapped[int] = mapped_column(Integer)
    step_id: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(40), index=True)
    state: Mapped[str] = mapped_column(String(40), index=True)
    page_url: Mapped[str] = mapped_column(String(2_048))
    source_url: Mapped[str] = mapped_column(String(2_048))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    content_hash_sha256: Mapped[str] = mapped_column(String(64), index=True)
    byte_size: Mapped[int] = mapped_column(Integer)
    media_type: Mapped[str] = mapped_column(String(200), index=True)
    source_locator: Mapped[str] = mapped_column(String(500))
    raw_retention_allowed: Mapped[bool] = mapped_column(Boolean)
    raw_retained: Mapped[bool] = mapped_column(Boolean)
    storage_uri: Mapped[str | None] = mapped_column(String(2_048), nullable=True)
    retention_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    screenshot_mode: Mapped[str | None] = mapped_column(String(40), nullable=True)
    viewport_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    viewport_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    element_selector: Mapped[str | None] = mapped_column(String(1_000), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    extracted_text_hash_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    excerpt: Mapped[str | None] = mapped_column(String(1_000), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

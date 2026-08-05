from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class RawObservationRecord(Base):
    __tablename__ = "raw_observations"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "source_record_key",
            "payload_hash_sha256",
            name="uq_raw_observation_deduplication",
        ),
        Index("ix_raw_observations_source_collected", "source_id", "collected_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    adapter_id: Mapped[str] = mapped_column(String(100))
    adapter_version: Mapped[str] = mapped_column(String(50))
    collection_job_id: Mapped[UUID] = mapped_column(index=True)
    source_record_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_record_type: Mapped[str] = mapped_column(String(100), index=True)
    source_record_action: Mapped[str] = mapped_column(
        String(32), default="upsert", index=True
    )
    supersedes_observation_id: Mapped[UUID | None] = mapped_column(
        nullable=True, index=True
    )
    source_url: Mapped[str] = mapped_column(String(2_048))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    payload_reference: Mapped[str | None] = mapped_column(String(2_048), nullable=True)
    payload_hash_sha256: Mapped[str] = mapped_column(String(64), index=True)
    schema_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content_language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    data_categories: Mapped[list[str]] = mapped_column(JSON)
    classification: Mapped[str] = mapped_column(String(32), default="internal")
    retention_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

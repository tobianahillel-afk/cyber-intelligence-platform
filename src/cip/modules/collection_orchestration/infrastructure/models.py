from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class CollectionJobRecord(Base):
    __tablename__ = "collection_jobs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_collection_jobs_idempotency_key"),
        Index("ix_collection_jobs_claim", "status", "available_at", "scheduled_for"),
        Index("ix_collection_jobs_source_schedule", "source_id", "adapter_id", "scheduled_for"),
        Index("ix_collection_jobs_lease_expiry", "status", "lease_expires_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    adapter_id: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64))
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    lease_seconds: Mapped[int] = mapped_column(Integer)
    max_attempts: Mapped[int] = mapped_column(Integer)
    base_delay_seconds: Mapped[int] = mapped_column(Integer)
    max_delay_seconds: Mapped[int] = mapped_column(Integer)
    circuit_failure_threshold: Mapped[int] = mapped_column(Integer)
    circuit_reset_seconds: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    observations_written: Mapped[int] = mapped_column(Integer, default=0)
    not_modified: Mapped[bool] = mapped_column(Boolean, default=False)


class CollectionCheckpointRecord(Base):
    __tablename__ = "collection_checkpoints"
    __table_args__ = (
        Index("ix_collection_checkpoints_last_success", "last_success_at"),
        Index("ix_collection_checkpoints_last_observation", "last_observation_at"),
    )

    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), primary_key=True)
    adapter_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_observation_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class CollectionCircuitRecord(Base):
    __tablename__ = "collection_circuits"
    __table_args__ = (Index("ix_collection_circuits_reopen", "state", "reopen_at"),)

    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), primary_key=True)
    adapter_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    state: Mapped[str] = mapped_column(String(32), index=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reopen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CollectionDeadLetterRecord(Base):
    __tablename__ = "collection_dead_letters"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_collection_dead_letters_job_id"),
        Index("ix_collection_dead_letters_source_failed", "source_id", "adapter_id", "failed_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("collection_jobs.id"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    adapter_id: Mapped[str] = mapped_column(String(100), index=True)
    failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    attempt: Mapped[int] = mapped_column(Integer)
    error_code: Mapped[str] = mapped_column(String(100))
    error_message: Mapped[str] = mapped_column(Text)
    checkpoint_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)

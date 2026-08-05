from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class SourcePortfolioRecord(Base):
    __tablename__ = "source_portfolio"

    source_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200))
    canonical_url: Mapped[str] = mapped_column(String(2_048))
    category: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    freshness_max_age_seconds: Mapped[int] = mapped_column(Integer)
    commercial_use_cases: Mapped[list[str]] = mapped_column(JSON)
    authorization_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    review_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    candidate_origin: Mapped[str | None] = mapped_column(String(200), nullable=True)
    monthly_cost_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    extra_metadata: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AdapterCapabilityRecord(Base):
    __tablename__ = "adapter_capabilities"
    __table_args__ = (
        UniqueConstraint("source_id", "adapter_id", name="uq_adapter_capability_identity"),
    )

    source_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    adapter_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    adapter_version: Mapped[str] = mapped_column(String(50))
    provider_schema_version: Mapped[str] = mapped_column(String(100))
    modes: Mapped[list[str]] = mapped_column(JSON)
    canonical_output_types: Mapped[list[str]] = mapped_column(JSON)
    supports_corrections: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_tombstones: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_retractions: Mapped[bool] = mapped_column(Boolean, default=False)
    max_page_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_window_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_per_request: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BackfillPartitionRecord(Base):
    __tablename__ = "backfill_partitions"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "adapter_id",
            "partition_key",
            name="uq_backfill_partition_identity",
        ),
        Index("ix_backfill_partition_claim", "state", "source_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(String(100), index=True)
    adapter_id: Mapped[str] = mapped_column(String(100), index=True)
    partition_key: Mapped[str] = mapped_column(String(300))
    lower_bound: Mapped[str] = mapped_column(String(300))
    upper_bound: Mapped[str] = mapped_column(String(300))
    state: Mapped[str] = mapped_column(String(40), index=True)
    cursor: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    records_written: Mapped[int] = mapped_column(Integer, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SourceHealthRecord(Base):
    __tablename__ = "source_health"

    source_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    freshness_state: Mapped[str] = mapped_column(String(50), index=True)
    schema_state: Mapped[str] = mapped_column(String(40), index=True)
    volume_state: Mapped[str] = mapped_column(String(40), index=True)
    field_population_state: Mapped[str] = mapped_column(String(40), index=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_source_record_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    quota_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_cost_used: Mapped[float] = mapped_column(Float, default=0.0)
    cost_window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_backfill_state: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class SourceQualityBaselineRecord(Base):
    __tablename__ = "source_quality_baselines"

    source_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    expected_records_per_run: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_records_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accepted_schema_fingerprints: Mapped[list[str]] = mapped_column(JSON, default=list)
    last_schema_fingerprints: Mapped[list[str]] = mapped_column(JSON, default=list)
    field_population_baseline: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    last_field_population: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class SourcePortfolioAuditRecord(Base):
    __tablename__ = "source_portfolio_audit"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    actor: Mapped[str] = mapped_column(String(200))
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

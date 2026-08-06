from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class ThreatIndicatorRecord(Base):
    __tablename__ = "threat_indicators"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    indicator_key: Mapped[str] = mapped_column(String(2_200), unique=True, index=True)
    indicator_type: Mapped[str] = mapped_column(String(80), index=True)
    indicator_value: Mapped[str] = mapped_column(String(2_048), index=True)
    state: Mapped[str] = mapped_column(String(80), index=True)
    observed_states: Mapped[str] = mapped_column(String(1_000))
    first_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_count: Mapped[int] = mapped_column(Integer)
    independent_source_count: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, index=True)
    shared_infrastructure: Mapped[bool] = mapped_column(Boolean, index=True)
    historical_only: Mapped[bool] = mapped_column(Boolean, index=True)
    has_conflict: Mapped[bool] = mapped_column(Boolean, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ThreatIndicatorSnapshotRecord(Base):
    __tablename__ = "threat_indicator_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_key", name="uq_threat_indicator_snapshot"),
        Index(
            "ix_threat_indicator_snapshot_source_record",
            "source_id",
            "source_record_key",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key_key=True)
    indicator_id: Mapped[UUID] = mapped_column(
        ForeignKey("threat_indicators.id", ondelete="CASCADE"), index=True
    )
    snapshot_key: Mapped[str] = mapped_column(String(64))
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    source_kind: Mapped[str] = mapped_column(String(80), index=True)
    source_record_key: Mapped[str] = mapped_column(String(500), index=True)
    source_url: Mapped[str] = mapped_column(String(2_048))
    indicator_type: Mapped[str] = mapped_column(String(80), index=True)
    indicator_value: Mapped[str] = mapped_column(String(2_048), index=True)
    state: Mapped[str] = mapped_column(String(80), index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    modified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    first_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    independence_key: Mapped[str] = mapped_column(String(500), index=True)
    sensor_scope: Mapped[str] = mapped_column(String(80), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    source_precedence: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, index=True)
    shared_infrastructure: Mapped[bool] = mapped_column(Boolean, index=True)
    historical_only: Mapped[bool] = mapped_column(Boolean, index=True)
    metadata_only: Mapped[bool] = mapped_column(Boolean)
    binary_payload_present: Mapped[bool] = mapped_column(Boolean)
    direct_validation_performed: Mapped[bool] = mapped_column(Boolean)
    supersedes_record_key: Mapped[str | None] = mapped_column(
        String(500), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ThreatIndicatorRelationRecord(Base):
    __tablename__ = "threat_indicator_relations"
    __table_args__ = (
        UniqueConstraint("relation_key", name="uq_threat_indicator_relation"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("threat_indicator_snapshots.id", ondelete="CASCADE"), index=True
    )
    relation_key: Mapped[str] = mapped_column(String(64))
    relation_type: Mapped[str] = mapped_column(String(80), index=True)
    target_key: Mapped[str] = mapped_column(String(500), index=True)
    confidence: Mapped[float] = mapped_column(Float)

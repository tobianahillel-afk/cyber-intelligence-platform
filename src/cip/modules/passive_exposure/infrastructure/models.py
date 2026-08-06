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
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class PassiveAssetRecord(Base):
    __tablename__ = "passive_assets"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    asset_key: Mapped[str] = mapped_column(String(2_200), unique=True, index=True)
    asset_kind: Mapped[str] = mapped_column(String(80), index=True)
    asset_value: Mapped[str] = mapped_column(String(2_048), index=True)
    state: Mapped[str] = mapped_column(String(80), index=True)
    observed_states: Mapped[str] = mapped_column(String(1_000))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_count: Mapped[int] = mapped_column(Integer)
    independent_source_count: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, index=True)
    historical_only: Mapped[bool] = mapped_column(Boolean, index=True)
    has_conflict: Mapped[bool] = mapped_column(Boolean, index=True)
    organization_link_status: Mapped[str] = mapped_column(String(80), index=True)
    exact_organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    candidate_organization_ids: Mapped[str] = mapped_column(Text)
    organization_link_reasons: Mapped[str] = mapped_column(Text)
    attribution_risks: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class PassiveObservationSnapshotRecord(Base):
    __tablename__ = "passive_observation_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_key", name="uq_passive_observation_snapshot"),
        Index(
            "ix_passive_observation_source_record",
            "source_id",
            "source_record_key",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("passive_assets.id", ondelete="CASCADE"), index=True
    )
    snapshot_key: Mapped[str] = mapped_column(String(64))
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    source_record_key: Mapped[str] = mapped_column(String(500), index=True)
    source_url: Mapped[str] = mapped_column(String(2_048))
    asset_kind: Mapped[str] = mapped_column(String(80), index=True)
    asset_value: Mapped[str] = mapped_column(String(2_048), index=True)
    observation_kind: Mapped[str] = mapped_column(String(80), index=True)
    state: Mapped[str] = mapped_column(String(80), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    modified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    independence_key: Mapped[str] = mapped_column(String(500), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    organization_link_status: Mapped[str] = mapped_column(String(80), index=True)
    organization_link_method: Mapped[str] = mapped_column(String(80), index=True)
    organization_link_confidence: Mapped[float] = mapped_column(Float)
    organization_link_reasons: Mapped[str] = mapped_column(Text)
    attribution_risks: Mapped[str] = mapped_column(Text)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    protocol: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, index=True)
    historical_only: Mapped[bool] = mapped_column(Boolean, index=True)
    metadata_only: Mapped[bool] = mapped_column(Boolean)
    passive_only: Mapped[bool] = mapped_column(Boolean)
    active_probe_performed: Mapped[bool] = mapped_column(Boolean)
    credentials_used: Mapped[bool] = mapped_column(Boolean)
    access_control_bypassed: Mapped[bool] = mapped_column(Boolean)
    exploit_attempted: Mapped[bool] = mapped_column(Boolean)
    direct_validation_performed: Mapped[bool] = mapped_column(Boolean)
    vulnerability_applicability_assessed: Mapped[bool] = mapped_column(Boolean)
    exposure_verified: Mapped[bool] = mapped_column(Boolean)
    supersedes_record_key: Mapped[str | None] = mapped_column(
        String(500), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PassiveTechnologyRecord(Base):
    __tablename__ = "passive_technologies"
    __table_args__ = (
        UniqueConstraint("technology_key", name="uq_passive_technology"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("passive_observation_snapshots.id", ondelete="CASCADE"),
        index=True,
    )
    technology_key: Mapped[str] = mapped_column(String(64))
    evidence_level: Mapped[str] = mapped_column(String(80), index=True)
    product_name: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    product_version: Mapped[str | None] = mapped_column(
        String(200), nullable=True, index=True
    )
    component_name: Mapped[str | None] = mapped_column(
        String(300), nullable=True, index=True
    )

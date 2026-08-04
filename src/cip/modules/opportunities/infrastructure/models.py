from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base
from cip.shared.persistence.types import UTCDateTime


class CommercialSignalRecord(Base):
    __tablename__ = "commercial_signals"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_commercial_signals_idempotency_key"),
        Index(
            "ix_commercial_signals_org_type_effective",
            "organization_id",
            "signal_type",
            "published_at",
            "collected_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    evidence_id: Mapped[UUID] = mapped_column(ForeignKey("evidence.id"), index=True)
    signal_type: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    matched_terms: Mapped[list[str]] = mapped_column(JSON, default=list)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    idempotency_key: Mapped[str] = mapped_column(String(64))


class NeedHypothesisRecord(Base):
    __tablename__ = "need_hypotheses"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_need_hypotheses_idempotency_key"),
        Index("ix_need_hypotheses_org_family", "organization_id", "family"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    family: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    rule_id: Mapped[str] = mapped_column(String(100))
    rule_version: Mapped[str] = mapped_column(String(50))
    rationale: Mapped[str] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64))


class NeedHypothesisSignalRecord(Base):
    __tablename__ = "need_hypothesis_signals"

    hypothesis_id: Mapped[UUID] = mapped_column(
        ForeignKey("need_hypotheses.id", ondelete="CASCADE"), primary_key=True
    )
    signal_id: Mapped[UUID] = mapped_column(
        ForeignKey("commercial_signals.id", ondelete="CASCADE"), primary_key=True
    )


class OpportunityRecord(Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        UniqueConstraint("hypothesis_id", name="uq_opportunities_hypothesis_id"),
        Index("ix_opportunities_priority", "state", "adjusted_score", "last_evidence_at"),
        Index("ix_opportunities_org_updated", "organization_id", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    hypothesis_id: Mapped[UUID] = mapped_column(ForeignKey("need_hypotheses.id"))
    state: Mapped[str] = mapped_column(String(32), index=True)
    recommended_offer: Mapped[str] = mapped_column(String(500))
    relevant_roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    trigger_summary: Mapped[str] = mapped_column(Text)
    next_action: Mapped[str] = mapped_column(String(500))
    confidence: Mapped[float] = mapped_column(Float)
    raw_score: Mapped[float] = mapped_column(Float)
    adjusted_score: Mapped[float] = mapped_column(Float, index=True)
    score_version: Mapped[str] = mapped_column(String(50))
    config_version: Mapped[str] = mapped_column(String(100))
    calculation_hash: Mapped[str] = mapped_column(String(64), index=True)
    generated_at: Mapped[datetime] = mapped_column(UTCDateTime())
    expires_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True, index=True
    )
    last_evidence_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    data_quality: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    snoozed_until: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True, index=True
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejected_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class OpportunityScoreComponentRecord(Base):
    __tablename__ = "opportunity_score_components"
    __table_args__ = (
        UniqueConstraint(
            "opportunity_id", "rule_id", name="uq_opportunity_component_rule"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    opportunity_id: Mapped[UUID] = mapped_column(
        ForeignKey("opportunities.id", ondelete="CASCADE"), index=True
    )
    rule_id: Mapped[str] = mapped_column(String(100))
    value: Mapped[float] = mapped_column(Float)
    weight: Mapped[float] = mapped_column(Float)
    contribution: Mapped[float] = mapped_column(Float)
    kind: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(Text)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    analyst_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    original_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_weight: Mapped[float | None] = mapped_column(Float, nullable=True)


class OpportunityEvidenceRecord(Base):
    __tablename__ = "opportunity_evidence"

    opportunity_id: Mapped[UUID] = mapped_column(
        ForeignKey("opportunities.id", ondelete="CASCADE"), primary_key=True
    )
    evidence_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True
    )


class OpportunityReviewRecord(Base):
    __tablename__ = "opportunity_reviews"
    __table_args__ = (
        Index("ix_opportunity_reviews_history", "opportunity_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    opportunity_id: Mapped[UUID] = mapped_column(ForeignKey("opportunities.id"), index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    previous_state: Mapped[str] = mapped_column(String(32))
    new_state: Mapped[str] = mapped_column(String(32))
    actor: Mapped[str] = mapped_column(String(200), index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    snoozed_until: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True
    )

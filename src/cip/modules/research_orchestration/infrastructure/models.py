from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class ResearchPlanRecord(Base):
    __tablename__ = "research_plans"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(String(1000))
    purpose: Mapped[str] = mapped_column(String(300), index=True)
    data_category: Mapped[str] = mapped_column(String(80), index=True)
    state: Mapped[str] = mapped_column(String(40), index=True)
    max_steps: Mapped[int] = mapped_column(Integer)
    max_automated_steps: Mapped[int] = mapped_column(Integer)
    max_total_cost: Mapped[float] = mapped_column(Float)
    max_step_cost: Mapped[float] = mapped_column(Float)
    allowed_source_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    allowed_tool_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    approved_step_keys: Mapped[list[str]] = mapped_column(JSON, default=list)
    allowed_hosts: Mapped[list[str]] = mapped_column(JSON, default=list)
    allowed_path_prefixes: Mapped[list[str]] = mapped_column(JSON, default=list)
    max_risk_level: Mapped[str] = mapped_column(String(30))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_revision_key: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ResearchPlanRevisionRecord(Base):
    __tablename__ = "research_plan_revisions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_plans.id", ondelete="CASCADE"), index=True
    )
    revision_key: Mapped[str] = mapped_column(String(64), unique=True)
    question: Mapped[str] = mapped_column(String(1000))
    purpose: Mapped[str] = mapped_column(String(300))
    data_category: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(40), index=True)
    budget: Mapped[dict[str, object]] = mapped_column(JSON)
    allowed_source_ids: Mapped[list[str]] = mapped_column(JSON)
    allowed_tool_ids: Mapped[list[str]] = mapped_column(JSON)
    approved_step_keys: Mapped[list[str]] = mapped_column(JSON)
    allowed_hosts: Mapped[list[str]] = mapped_column(JSON)
    allowed_path_prefixes: Mapped[list[str]] = mapped_column(JSON)
    max_risk_level: Mapped[str] = mapped_column(String(30))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actor: Mapped[str] = mapped_column(String(200))
    change_reason: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ResearchStepRecord(Base):
    __tablename__ = "research_steps"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_plans.id", ondelete="CASCADE"), index=True
    )
    step_key: Mapped[str] = mapped_column(String(150), index=True)
    sequence: Mapped[int] = mapped_column(Integer, index=True)
    source_id: Mapped[str] = mapped_column(String(100), index=True)
    tool_id: Mapped[str] = mapped_column(String(150), index=True)
    mode: Mapped[str] = mapped_column(String(40), index=True)
    purpose: Mapped[str] = mapped_column(String(300))
    data_category: Mapped[str] = mapped_column(String(80))
    estimated_cost: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(30))
    target_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    query_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingestion_path_id: Mapped[str | None] = mapped_column(String(150), nullable=True)
    state: Mapped[str] = mapped_column(String(40), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ResearchPlanDecisionRecord(Base):
    __tablename__ = "research_plan_decisions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_plans.id", ondelete="CASCADE"), index=True
    )
    decision_key: Mapped[str] = mapped_column(String(64), unique=True)
    decision_type: Mapped[str] = mapped_column(String(40), index=True)
    actor: Mapped[str] = mapped_column(String(200))
    reason: Mapped[str] = mapped_column(String(1000))
    previous_state: Mapped[str] = mapped_column(String(40))
    resulting_state: Mapped[str] = mapped_column(String(40), index=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ResearchStepDecisionRecord(Base):
    __tablename__ = "research_step_decisions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_plans.id", ondelete="CASCADE"), index=True
    )
    step_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_steps.id", ondelete="CASCADE"), index=True
    )
    decision_key: Mapped[str] = mapped_column(String(64), unique=True)
    allowed: Mapped[bool] = mapped_column(Boolean, index=True)
    next_state: Mapped[str] = mapped_column(String(40), index=True)
    reasons: Mapped[list[str]] = mapped_column(JSON)
    usage_snapshot: Mapped[dict[str, object]] = mapped_column(JSON)
    runtime_snapshot: Mapped[dict[str, object]] = mapped_column(JSON)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ResearchStepAttemptRecord(Base):
    __tablename__ = "research_step_attempts"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_plans.id", ondelete="CASCADE"), index=True
    )
    step_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_steps.id", ondelete="CASCADE"), index=True
    )
    attempt_key: Mapped[str] = mapped_column(String(64), unique=True)
    mode: Mapped[str] = mapped_column(String(40), index=True)
    state: Mapped[str] = mapped_column(String(40), index=True)
    actor: Mapped[str] = mapped_column(String(200))
    external_action_started: Mapped[bool] = mapped_column(Boolean, default=False)
    external_action_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ResearchResultRecord(Base):
    __tablename__ = "research_results"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_plans.id", ondelete="CASCADE"), index=True
    )
    step_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_steps.id", ondelete="CASCADE"), index=True
    )
    attempt_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("research_step_attempts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    result_key: Mapped[str] = mapped_column(String(64), unique=True)
    result_type: Mapped[str] = mapped_column(String(60), index=True)
    evidence_reference: Mapped[str] = mapped_column(String(500), index=True)
    provenance_reference: Mapped[str] = mapped_column(String(500))
    source_id: Mapped[str] = mapped_column(String(100), index=True)
    summary: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    recorded_by: Mapped[str] = mapped_column(String(200))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

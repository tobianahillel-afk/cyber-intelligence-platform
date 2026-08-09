from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from cip.shared.persistence.base import Base


class ConditionalProviderApprovalRecord(Base):
    __tablename__ = "conditional_provider_approvals"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    provider_kind: Mapped[str] = mapped_column(String(40), index=True)
    access_method: Mapped[str] = mapped_column(String(60), index=True)
    state: Mapped[str] = mapped_column(String(40), index=True)
    authorization_document_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    licence_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    terms_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    terms_state: Mapped[str] = mapped_column(String(40), index=True)
    approved_scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    approved_fields: Mapped[list[str]] = mapped_column(JSON, default=list)
    approved_purposes: Mapped[list[str]] = mapped_column(JSON, default=list)
    approved_data_categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    automated_collection_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    account_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    current_revision_key: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ConditionalProviderApprovalRevisionRecord(Base):
    __tablename__ = "conditional_provider_approval_revisions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    approval_id: Mapped[UUID] = mapped_column(
        ForeignKey("conditional_provider_approvals.id", ondelete="CASCADE"), index=True
    )
    revision_key: Mapped[str] = mapped_column(String(64), unique=True)
    source_id: Mapped[str] = mapped_column(String(100), index=True)
    provider_kind: Mapped[str] = mapped_column(String(40), index=True)
    access_method: Mapped[str] = mapped_column(String(60), index=True)
    state: Mapped[str] = mapped_column(String(40), index=True)
    authorization_document_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    licence_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    terms_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    terms_state: Mapped[str] = mapped_column(String(40), index=True)
    approved_scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    approved_fields: Mapped[list[str]] = mapped_column(JSON, default=list)
    approved_purposes: Mapped[list[str]] = mapped_column(JSON, default=list)
    approved_data_categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    automated_collection_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    account_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ConditionalProviderRuntimeControlRecord(Base):
    __tablename__ = "conditional_provider_runtime_controls"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    approval_id: Mapped[UUID] = mapped_column(
        ForeignKey("conditional_provider_approvals.id", ondelete="CASCADE"), unique=True
    )
    source_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    paused: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    kill_switch_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    paused_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ConditionalProviderControlDecisionRecord(Base):
    __tablename__ = "conditional_provider_control_decisions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    control_id: Mapped[UUID] = mapped_column(
        ForeignKey("conditional_provider_runtime_controls.id", ondelete="CASCADE"), index=True
    )
    decision_key: Mapped[str] = mapped_column(String(64), unique=True)
    source_id: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    actor: Mapped[str] = mapped_column(String(200))
    reason: Mapped[str] = mapped_column(String(1000))
    resulting_paused: Mapped[bool] = mapped_column(Boolean)
    resulting_kill_switch_active: Mapped[bool] = mapped_column(Boolean)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ConditionalExecutionDecisionRecord(Base):
    __tablename__ = "conditional_execution_decisions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    approval_id: Mapped[UUID] = mapped_column(
        ForeignKey("conditional_provider_approvals.id", ondelete="CASCADE"), index=True
    )
    decision_key: Mapped[str] = mapped_column(String(64), unique=True)
    source_id: Mapped[str] = mapped_column(String(100), index=True)
    access_method: Mapped[str] = mapped_column(String(60), index=True)
    purpose: Mapped[str] = mapped_column(String(300), index=True)
    data_category: Mapped[str] = mapped_column(String(80), index=True)
    requested_scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    requested_fields: Mapped[list[str]] = mapped_column(JSON, default=list)
    retention_days: Mapped[int] = mapped_column(Integer)
    automated: Mapped[bool] = mapped_column(Boolean)
    account_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    onboarding_state: Mapped[str] = mapped_column(String(60), index=True)
    source_policy_allowed: Mapped[bool] = mapped_column(Boolean)
    adapter_capability_present: Mapped[bool] = mapped_column(Boolean)
    kill_switch_active: Mapped[bool] = mapped_column(Boolean)
    quota_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_cost_used: Mapped[float] = mapped_column(Float)
    monthly_cost_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    allowed: Mapped[bool] = mapped_column(Boolean, index=True)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from cip.modules.conditional_integrations.domain import (
    ApprovalState,
    ConditionalAccessMethod,
    ConditionalProviderKind,
    ProviderControlAction,
    TermsReviewState,
)
from cip.modules.source_governance.domain.models import DataCategory


class ApprovalUpsertRequest(BaseModel):
    provider_kind: ConditionalProviderKind
    access_method: ConditionalAccessMethod
    state: ApprovalState
    authorization_document_reference: str | None = Field(default=None, max_length=500)
    licence_reference: str | None = Field(default=None, max_length=500)
    terms_reference: str | None = Field(default=None, max_length=500)
    terms_state: TermsReviewState
    approved_scopes: set[str] = Field(default_factory=set)
    approved_fields: set[str] = Field(default_factory=set)
    approved_purposes: set[str] = Field(default_factory=set)
    approved_data_categories: set[DataCategory] = Field(default_factory=set)
    retention_days: int | None = Field(default=None, ge=1)
    automated_collection_allowed: bool = False
    account_reference: str | None = Field(default=None, max_length=500)
    reviewed_at: datetime | None = None
    review_due_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    paused_reason: str | None = Field(default=None, max_length=500)
    actor: str = Field(min_length=1, max_length=200)
    change_reason: str = Field(min_length=1, max_length=1000)


class ProviderControlRequest(BaseModel):
    action: ProviderControlAction
    actor: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=1000)


class EligibilityRequest(BaseModel):
    access_method: ConditionalAccessMethod
    purpose: str = Field(min_length=1, max_length=300)
    data_category: DataCategory
    target_url: str = Field(min_length=1, max_length=2048)
    requested_scopes: set[str] = Field(default_factory=set)
    requested_fields: set[str] = Field(default_factory=set)
    retention_days: int = Field(ge=1)
    automated: bool = True
    store_raw_content: bool = False
    account_reference: str | None = Field(default=None, max_length=500)


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: str
    provider_kind: str
    access_method: str
    state: str
    authorization_document_reference: str | None
    licence_reference: str | None
    terms_reference: str | None
    terms_state: str
    approved_scopes: list[str]
    approved_fields: list[str]
    approved_purposes: list[str]
    approved_data_categories: list[str]
    retention_days: int | None
    automated_collection_allowed: bool
    account_reference: str | None
    reviewed_at: datetime | None
    review_due_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    paused_reason: str | None
    current_revision_key: str
    created_at: datetime
    updated_at: datetime


class ApprovalRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    revision_key: str
    state: str
    access_method: str
    terms_state: str
    approved_scopes: list[str]
    approved_fields: list[str]
    approved_purposes: list[str]
    approved_data_categories: list[str]
    retention_days: int | None
    automated_collection_allowed: bool
    account_reference: str | None
    reviewed_at: datetime | None
    review_due_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    paused_reason: str | None
    actor: str
    change_reason: str
    created_at: datetime


class RuntimeControlResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: str
    paused: bool
    kill_switch_active: bool
    paused_reason: str | None
    updated_at: datetime


class ControlDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision_key: str
    action: str
    actor: str
    reason: str
    resulting_paused: bool
    resulting_kill_switch_active: bool
    decided_at: datetime
    created_at: datetime


class ExecutionDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision_key: str
    access_method: str
    purpose: str
    data_category: str
    target_url: str
    requested_scopes: list[str]
    requested_fields: list[str]
    retention_days: int
    automated: bool
    store_raw_content: bool
    account_reference: str | None
    onboarding_state: str
    source_policy_allowed: bool
    source_portfolio_allowed: bool
    adapter_capability_present: bool
    provider_paused: bool
    kill_switch_active: bool
    quota_remaining: int | None
    monthly_cost_used: float
    monthly_cost_limit: float | None
    allowed: bool
    reasons: list[str]
    evaluated_at: datetime


class SourceValueSummaryResponse(BaseModel):
    executions: int
    modified_executions: int
    observations_written: int
    commercial_projections: int
    identity_projections: int
    request_cost: float


class ConditionalProviderValueResponse(BaseModel):
    source_id: str
    evidence_available: bool
    source: SourceValueSummaryResponse
    portfolio_without_source: SourceValueSummaryResponse


class ConditionalProviderSummary(BaseModel):
    approval: ApprovalResponse
    control: RuntimeControlResponse | None


class ConditionalProviderDetail(ConditionalProviderSummary):
    revisions: list[ApprovalRevisionResponse]
    control_decisions: list[ControlDecisionResponse]
    execution_decisions: list[ExecutionDecisionResponse]


class ConditionalProviderListResponse(BaseModel):
    items: list[ConditionalProviderSummary]
    total: int

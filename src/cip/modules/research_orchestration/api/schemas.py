from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from cip.modules.research_orchestration.domain import (
    ResearchDecisionType,
    ResearchRiskLevel,
    ResearchStepMode,
)
from cip.modules.source_governance.domain.models import DataCategory


class ResearchBudgetInput(BaseModel):
    max_steps: int = Field(ge=1)
    max_automated_steps: int = Field(ge=0)
    max_total_cost: float = Field(ge=0)
    max_step_cost: float = Field(ge=0)


class ResearchPlanUpsertRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    purpose: str = Field(min_length=1, max_length=300)
    data_category: DataCategory
    budget: ResearchBudgetInput
    allowed_source_ids: set[str] = Field(default_factory=set)
    allowed_tool_ids: set[str] = Field(default_factory=set)
    approved_step_keys: set[str] = Field(default_factory=set)
    allowed_hosts: set[str] = Field(default_factory=set)
    allowed_path_prefixes: list[str] = Field(default_factory=list)
    max_risk_level: ResearchRiskLevel = ResearchRiskLevel.MEDIUM
    expires_at: datetime | None = None
    actor: str = Field(min_length=1, max_length=200)
    change_reason: str = Field(min_length=1, max_length=1000)


class ResearchPlanDecisionRequest(BaseModel):
    decision_type: ResearchDecisionType
    actor: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=1000)


class ResearchStepCreateRequest(BaseModel):
    step_key: str = Field(min_length=1, max_length=150)
    sequence: int = Field(ge=1)
    source_id: str = Field(min_length=1, max_length=100)
    tool_id: str = Field(min_length=1, max_length=150)
    mode: ResearchStepMode
    purpose: str = Field(min_length=1, max_length=300)
    data_category: DataCategory
    estimated_cost: float = Field(ge=0)
    risk_level: ResearchRiskLevel
    target_url: str | None = Field(default=None, max_length=2048)
    query_text: str | None = Field(default=None, max_length=2000)
    ingestion_path_id: str | None = Field(default=None, max_length=150)


class ResearchAttemptCreateRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=200)
    idempotency_key: str = Field(min_length=1, max_length=300)


class ResearchResultCreateRequest(BaseModel):
    attempt_id: UUID | None = None
    result_type: str = Field(min_length=1, max_length=60)
    evidence_reference: str = Field(min_length=1, max_length=500)
    provenance_reference: str = Field(min_length=1, max_length=500)
    source_id: str = Field(min_length=1, max_length=100)
    summary: str | None = Field(default=None, max_length=1000)
    recorded_by: str = Field(min_length=1, max_length=200)


class ResearchPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question: str
    purpose: str
    data_category: str
    state: str
    max_steps: int
    max_automated_steps: int
    max_total_cost: float
    max_step_cost: float
    allowed_source_ids: list[str]
    allowed_tool_ids: list[str]
    approved_step_keys: list[str]
    allowed_hosts: list[str]
    allowed_path_prefixes: list[str]
    max_risk_level: str
    expires_at: datetime | None
    current_revision_key: str
    created_at: datetime
    updated_at: datetime


class ResearchPlanRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    revision_key: str
    question: str
    purpose: str
    data_category: str
    state: str
    budget: dict[str, object]
    allowed_source_ids: list[str]
    allowed_tool_ids: list[str]
    approved_step_keys: list[str]
    allowed_hosts: list[str]
    allowed_path_prefixes: list[str]
    max_risk_level: str
    expires_at: datetime | None
    actor: str
    change_reason: str
    created_at: datetime


class ResearchStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    step_key: str
    sequence: int
    source_id: str
    tool_id: str
    mode: str
    purpose: str
    data_category: str
    estimated_cost: float
    risk_level: str
    target_url: str | None
    query_text: str | None
    ingestion_path_id: str | None
    state: str
    created_at: datetime
    updated_at: datetime


class ResearchPlanDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision_key: str
    decision_type: str
    actor: str
    reason: str
    previous_state: str
    resulting_state: str
    decided_at: datetime
    created_at: datetime


class ResearchStepDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision_key: str
    allowed: bool
    next_state: str
    reasons: list[str]
    usage_snapshot: dict[str, object]
    runtime_snapshot: dict[str, object]
    evaluated_at: datetime
    created_at: datetime


class ResearchAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    step_id: UUID
    attempt_key: str
    mode: str
    state: str
    actor: str
    external_action_started: bool
    external_action_reference: str | None
    error_code: str | None
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ResearchResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    step_id: UUID
    attempt_id: UUID | None
    result_key: str
    result_type: str
    evidence_reference: str
    provenance_reference: str
    source_id: str
    summary: str | None
    recorded_by: str
    recorded_at: datetime


class ResearchUsageResponse(BaseModel):
    completed_steps: int
    automated_steps: int
    cost_used: float


class ResearchRuntimeResponse(BaseModel):
    source_authorized: bool
    source_executable: bool
    adapter_capability_present: bool
    manual_link_allowed: bool
    ingestion_path_approved: bool
    quota_remaining: int | None


class ResearchEvaluationResponse(BaseModel):
    allowed: bool
    next_state: str
    reasons: list[str]
    usage: ResearchUsageResponse
    runtime: ResearchRuntimeResponse


class ResearchPlanListResponse(BaseModel):
    items: list[ResearchPlanResponse]
    total: int


class ResearchPlanDetail(BaseModel):
    plan: ResearchPlanResponse
    usage: ResearchUsageResponse
    revisions: list[ResearchPlanRevisionResponse]
    steps: list[ResearchStepResponse]
    plan_decisions: list[ResearchPlanDecisionResponse]
    step_decisions: list[ResearchStepDecisionResponse]
    attempts: list[ResearchAttemptResponse]
    results: list[ResearchResultResponse]

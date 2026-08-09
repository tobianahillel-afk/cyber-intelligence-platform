from __future__ import annotations

from enum import StrEnum


class ResearchPlanState(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ResearchStepMode(StrEnum):
    PERSISTED_SEARCH = "persisted_search"
    MANUAL_LINK = "manual_link"
    AUTOMATED_ADAPTER = "automated_adapter"
    APPROVED_INGESTION = "approved_ingestion"


class ResearchStepState(StrEnum):
    PLANNED = "planned"
    READY = "ready"
    MANUAL_ACTION_REQUIRED = "manual_action_required"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class ResearchRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PROHIBITED = "prohibited"


class ResearchDecisionType(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    PAUSE = "pause"
    RESUME = "resume"
    COMPLETE = "complete"
    CANCEL = "cancel"


class ResearchBlockReason(StrEnum):
    ALLOWED = "allowed"
    PLAN_NOT_APPROVED = "plan_not_approved"
    PLAN_EXPIRED = "plan_expired"
    STEP_NOT_APPROVED = "step_not_approved"
    STEP_NOT_IN_PLAN = "step_not_in_plan"
    SOURCE_NOT_ALLOWED = "source_not_allowed"
    TOOL_NOT_ALLOWED = "tool_not_allowed"
    PURPOSE_MISMATCH = "purpose_mismatch"
    CATEGORY_MISMATCH = "category_mismatch"
    TARGET_URL_REQUIRED = "target_url_required"
    TARGET_SCHEME_NOT_ALLOWED = "target_scheme_not_allowed"
    TARGET_HOST_NOT_ALLOWED = "target_host_not_allowed"
    TARGET_PATH_NOT_ALLOWED = "target_path_not_allowed"
    STEP_BUDGET_EXHAUSTED = "step_budget_exhausted"
    AUTOMATION_BUDGET_EXHAUSTED = "automation_budget_exhausted"
    STEP_COST_EXCEEDS_LIMIT = "step_cost_exceeds_limit"
    TOTAL_COST_BUDGET_EXHAUSTED = "total_cost_budget_exhausted"
    RISK_NOT_ALLOWED = "risk_not_allowed"
    SOURCE_AUTHORIZATION_REQUIRED = "source_authorization_required"
    SOURCE_NOT_EXECUTABLE = "source_not_executable"
    ADAPTER_CAPABILITY_MISSING = "adapter_capability_missing"
    QUOTA_EXHAUSTED = "quota_exhausted"
    MANUAL_LINK_REQUIRED = "manual_link_required"
    INGESTION_PATH_NOT_APPROVED = "ingestion_path_not_approved"

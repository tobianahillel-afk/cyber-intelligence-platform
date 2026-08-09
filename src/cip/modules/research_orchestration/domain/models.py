from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse
from uuid import UUID

from cip.modules.research_orchestration.domain.enums import (
    ResearchBlockReason,
    ResearchPlanState,
    ResearchRiskLevel,
    ResearchStepMode,
    ResearchStepState,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.shared.kernel.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class ResearchBudget:
    max_steps: int
    max_automated_steps: int
    max_total_cost: float
    max_step_cost: float

    def __post_init__(self) -> None:
        if self.max_steps < 1:
            raise ValueError("max_steps must be positive")
        if not 0 <= self.max_automated_steps <= self.max_steps:
            raise ValueError("max_automated_steps must be between zero and max_steps")
        if self.max_total_cost < 0:
            raise ValueError("max_total_cost cannot be negative")
        if self.max_step_cost < 0 or self.max_step_cost > self.max_total_cost:
            raise ValueError("max_step_cost must be within the total cost budget")


@dataclass(frozen=True, slots=True)
class ResearchPlan:
    plan_id: UUID
    question: str
    purpose: str
    data_category: DataCategory
    state: ResearchPlanState
    budget: ResearchBudget
    allowed_source_ids: frozenset[str]
    allowed_tool_ids: frozenset[str]
    approved_step_keys: frozenset[str]
    allowed_hosts: frozenset[str] = field(default_factory=frozenset)
    allowed_path_prefixes: tuple[str, ...] = ()
    max_risk_level: ResearchRiskLevel = ResearchRiskLevel.MEDIUM
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        _normalize_text(self, "question", maximum=1000)
        _normalize_text(self, "purpose", maximum=300)
        _normalize_set(self, "allowed_source_ids", maximum=100)
        _normalize_set(self, "allowed_tool_ids", maximum=150)
        _normalize_set(self, "approved_step_keys", maximum=150)
        object.__setattr__(
            self,
            "allowed_hosts",
            frozenset(_normalize_host(value) for value in self.allowed_hosts),
        )
        prefixes = tuple(
            dict.fromkeys(_normalize_path(value) for value in self.allowed_path_prefixes)
        )
        object.__setattr__(self, "allowed_path_prefixes", prefixes)
        if self.expires_at is not None:
            object.__setattr__(
                self,
                "expires_at",
                require_aware_utc(self.expires_at, field_name="expires_at"),
            )


@dataclass(frozen=True, slots=True)
class ResearchStep:
    step_key: str
    sequence: int
    source_id: str
    tool_id: str
    mode: ResearchStepMode
    purpose: str
    data_category: DataCategory
    estimated_cost: float
    risk_level: ResearchRiskLevel
    target_url: str | None = None
    query_text: str | None = None
    ingestion_path_id: str | None = None

    def __post_init__(self) -> None:
        _normalize_text(self, "step_key", maximum=150)
        _normalize_text(self, "source_id", maximum=100)
        _normalize_text(self, "tool_id", maximum=150)
        _normalize_text(self, "purpose", maximum=300)
        if self.sequence < 1:
            raise ValueError("sequence must be positive")
        if self.estimated_cost < 0:
            raise ValueError("estimated_cost cannot be negative")
        _normalize_optional_text(self, "query_text", maximum=2000)
        _normalize_optional_text(self, "ingestion_path_id", maximum=150)
        _normalize_target_url(self)
        if self.mode is ResearchStepMode.MANUAL_LINK and self.target_url is None:
            raise ValueError("manual_link step requires target_url")
        if self.mode is ResearchStepMode.AUTOMATED_ADAPTER and self.target_url is None:
            raise ValueError("automated_adapter step requires target_url")
        if self.mode is ResearchStepMode.APPROVED_INGESTION and self.ingestion_path_id is None:
            raise ValueError("approved_ingestion step requires ingestion_path_id")


@dataclass(frozen=True, slots=True)
class ResearchUsage:
    completed_steps: int = 0
    automated_steps: int = 0
    cost_used: float = 0.0

    def __post_init__(self) -> None:
        if self.completed_steps < 0 or self.automated_steps < 0:
            raise ValueError("step counters cannot be negative")
        if self.cost_used < 0:
            raise ValueError("cost_used cannot be negative")


@dataclass(frozen=True, slots=True)
class ResearchRuntimeState:
    source_authorized: bool
    source_executable: bool
    adapter_capability_present: bool
    manual_link_allowed: bool
    ingestion_path_approved: bool
    quota_remaining: int | None

    def __post_init__(self) -> None:
        if self.quota_remaining is not None and self.quota_remaining < 0:
            raise ValueError("quota_remaining cannot be negative")


@dataclass(frozen=True, slots=True)
class ResearchStepDecision:
    allowed: bool
    next_state: ResearchStepState
    reasons: tuple[ResearchBlockReason, ...]

    def __post_init__(self) -> None:
        if self.allowed:
            if self.reasons != (ResearchBlockReason.ALLOWED,):
                raise ValueError("allowed decision must contain only allowed")
            allowed_states = {
                ResearchStepState.READY,
                ResearchStepState.MANUAL_ACTION_REQUIRED,
            }
            if self.next_state not in allowed_states:
                raise ValueError("allowed decision requires ready or manual-action state")
        elif not self.reasons or ResearchBlockReason.ALLOWED in self.reasons:
            raise ValueError("blocked decision requires blocking reasons")


@dataclass(frozen=True, slots=True)
class ResearchSourceCandidate:
    source_id: str
    tool_id: str
    mode: ResearchStepMode
    authorized: bool
    executable: bool
    manual_link_allowed: bool
    freshness_score: float
    value_score: float
    estimated_cost: float
    quota_remaining: int | None
    risk_level: ResearchRiskLevel

    def __post_init__(self) -> None:
        _normalize_text(self, "source_id", maximum=100)
        _normalize_text(self, "tool_id", maximum=150)
        for field_name in ("freshness_score", "value_score"):
            value = getattr(self, field_name)
            if not 0 <= value <= 1:
                raise ValueError(f"{field_name} must be between zero and one")
        if self.estimated_cost < 0:
            raise ValueError("estimated_cost cannot be negative")
        if self.quota_remaining is not None and self.quota_remaining < 0:
            raise ValueError("quota_remaining cannot be negative")


@dataclass(frozen=True, slots=True)
class ApprovedIngestionPath:
    path_id: str
    source_id: str
    allowed_data_categories: frozenset[DataCategory]
    allowed_purposes: frozenset[str]

    def __post_init__(self) -> None:
        _normalize_text(self, "path_id", maximum=150)
        _normalize_text(self, "source_id", maximum=100)
        _normalize_set(self, "allowed_purposes", maximum=300)
        if not self.allowed_data_categories or not self.allowed_purposes:
            raise ValueError("ingestion path requires category and purpose scopes")


def _normalize_text(instance: object, field_name: str, *, maximum: int) -> None:
    value = getattr(instance, field_name).strip()
    if not value:
        raise ValueError(f"{field_name} is required")
    if len(value) > maximum:
        raise ValueError(f"{field_name} cannot exceed {maximum} characters")
    object.__setattr__(instance, field_name, value)


def _normalize_optional_text(instance: object, field_name: str, *, maximum: int) -> None:
    value = getattr(instance, field_name)
    if value is None:
        return
    normalized = value.strip()
    if not normalized:
        object.__setattr__(instance, field_name, None)
        return
    if len(normalized) > maximum:
        raise ValueError(f"{field_name} cannot exceed {maximum} characters")
    object.__setattr__(instance, field_name, normalized)


def _normalize_set(instance: object, field_name: str, *, maximum: int) -> None:
    values = getattr(instance, field_name)
    normalized = frozenset(value.strip() for value in values if value.strip())
    if any(len(value) > maximum for value in normalized):
        raise ValueError(f"{field_name} value cannot exceed {maximum} characters")
    object.__setattr__(instance, field_name, normalized)


def _normalize_host(value: str) -> str:
    normalized = value.strip().lower().rstrip(".")
    if not normalized or "/" in normalized or ":" in normalized:
        raise ValueError("allowed_hosts must contain hostnames only")
    return normalized


def _normalize_path(value: str) -> str:
    normalized = value.strip()
    if not normalized.startswith("/"):
        raise ValueError("allowed_path_prefixes must start with /")
    return normalized


def _normalize_target_url(instance: ResearchStep) -> None:
    if instance.target_url is None:
        return
    value = instance.target_url.strip()
    parsed = urlparse(value)
    if len(value) > 2048 or not parsed.scheme or not parsed.hostname:
        raise ValueError("target_url must be an absolute URL")
    object.__setattr__(instance, "target_url", value)

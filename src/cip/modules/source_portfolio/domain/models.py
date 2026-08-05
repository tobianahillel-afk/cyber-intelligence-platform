from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType

from cip.shared.kernel.time import require_aware_utc


class CatalogStatus(StrEnum):
    CANDIDATE = "candidate"
    EXECUTABLE = "executable"
    PAUSED = "paused"
    DISABLED = "disabled"


class CollectionMode(StrEnum):
    HISTORICAL_BACKFILL = "historical_backfill"
    INCREMENTAL_CURSOR = "incremental_cursor"
    CONDITIONAL_REFRESH = "conditional_refresh"
    WEBHOOK = "webhook"
    ENTITY_LOOKUP = "entity_lookup"
    PRIORITY_REFRESH = "priority_refresh"


class FreshnessState(StrEnum):
    FRESH = "fresh"
    AGING = "aging"
    STALE_REFRESH_QUEUED = "stale_refresh_queued"
    SOURCE_UNAVAILABLE = "source_unavailable"
    AUTHORIZATION_EXPIRED = "authorization_expired"
    QUOTA_EXHAUSTED = "quota_exhausted"
    COST_BUDGET_EXHAUSTED = "cost_budget_exhausted"
    HISTORICAL_ONLY = "historical_only"


class SchemaState(StrEnum):
    UNKNOWN = "unknown"
    STABLE = "stable"
    DRIFTED = "drifted"


class AnomalyState(StrEnum):
    UNKNOWN = "unknown"
    NORMAL = "normal"
    ANOMALOUS = "anomalous"


class BackfillState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in {
            BackfillState.COMPLETED,
            BackfillState.CANCELLED,
        }


@dataclass(frozen=True, slots=True)
class AdapterCapabilityManifest:
    source_id: str
    adapter_id: str
    adapter_version: str
    provider_schema_version: str
    modes: frozenset[CollectionMode]
    canonical_output_types: tuple[str, ...]
    supports_corrections: bool = False
    supports_tombstones: bool = False
    supports_retractions: bool = False
    max_page_size: int | None = None
    max_window_days: int | None = None
    cost_per_request: float = 0.0

    def __post_init__(self) -> None:
        for field_name in (
            "source_id",
            "adapter_id",
            "adapter_version",
            "provider_schema_version",
        ):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} is required")
            object.__setattr__(self, field_name, value)
        outputs = tuple(dict.fromkeys(value.strip() for value in self.canonical_output_types))
        if not outputs or any(not value for value in outputs):
            raise ValueError("canonical_output_types must contain non-empty values")
        if self.max_page_size is not None and self.max_page_size < 1:
            raise ValueError("max_page_size must be positive")
        if self.max_window_days is not None and self.max_window_days < 1:
            raise ValueError("max_window_days must be positive")
        if self.cost_per_request < 0:
            raise ValueError("cost_per_request cannot be negative")
        object.__setattr__(self, "canonical_output_types", outputs)

    def supports(self, mode: CollectionMode) -> bool:
        return mode in self.modes


@dataclass(frozen=True, slots=True)
class SourceCatalogEntry:
    source_id: str
    display_name: str
    canonical_url: str
    category: str
    status: CatalogStatus
    freshness_max_age_seconds: int
    commercial_use_cases: tuple[str, ...]
    adapter: AdapterCapabilityManifest | None = None
    authorization_expires_at: datetime | None = None
    review_due_at: datetime | None = None
    candidate_origin: str | None = None
    monthly_cost_limit: float | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("source_id", "display_name", "canonical_url", "category"):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} is required")
            object.__setattr__(self, field_name, value)
        if not self.canonical_url.startswith("https://"):
            raise ValueError("canonical_url must use HTTPS")
        if self.freshness_max_age_seconds < 1:
            raise ValueError("freshness_max_age_seconds must be positive")
        use_cases = tuple(dict.fromkeys(value.strip() for value in self.commercial_use_cases))
        if not use_cases or any(not value for value in use_cases):
            raise ValueError("commercial_use_cases must contain non-empty values")
        if self.status is CatalogStatus.EXECUTABLE and self.adapter is None:
            raise ValueError("executable sources require an adapter manifest")
        if self.adapter is not None and self.adapter.source_id != self.source_id:
            raise ValueError("adapter source_id must match catalog source_id")
        if self.status is CatalogStatus.CANDIDATE and self.candidate_origin is None:
            raise ValueError("candidate sources require candidate_origin")
        if self.monthly_cost_limit is not None and self.monthly_cost_limit < 0:
            raise ValueError("monthly_cost_limit cannot be negative")
        object.__setattr__(self, "commercial_use_cases", use_cases)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        for field_name in ("authorization_expires_at", "review_due_at"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    require_aware_utc(value, field_name=field_name),
                )

    @property
    def executable(self) -> bool:
        return self.status is CatalogStatus.EXECUTABLE and self.adapter is not None


@dataclass(frozen=True, slots=True)
class SourceHealth:
    source_id: str
    freshness_state: FreshnessState
    schema_state: SchemaState
    volume_state: AnomalyState = AnomalyState.UNKNOWN
    field_population_state: AnomalyState = AnomalyState.UNKNOWN
    circuit_state: str = "unknown"
    last_attempt_at: datetime | None = None
    last_success_at: datetime | None = None
    last_source_record_at: datetime | None = None
    consecutive_failures: int = 0
    quota_remaining: int | None = None
    monthly_cost_used: float = 0.0
    cost_window_started_at: datetime | None = None
    current_backfill_state: BackfillState | None = None
    last_error_code: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not self.circuit_state.strip():
            raise ValueError("circuit_state is required")
        if self.consecutive_failures < 0:
            raise ValueError("consecutive_failures cannot be negative")
        if self.quota_remaining is not None and self.quota_remaining < 0:
            raise ValueError("quota_remaining cannot be negative")
        if self.monthly_cost_used < 0:
            raise ValueError("monthly_cost_used cannot be negative")
        for field_name in (
            "last_attempt_at",
            "last_success_at",
            "last_source_record_at",
            "cost_window_started_at",
        ):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    require_aware_utc(value, field_name=field_name),
                )

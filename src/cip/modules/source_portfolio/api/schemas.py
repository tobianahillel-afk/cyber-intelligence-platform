from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from cip.modules.source_portfolio.domain.models import (
    AdapterCapabilityManifest,
    SourceCatalogEntry,
    SourceHealth,
)


class ActorRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=200)


class BackfillPartitionRequest(BaseModel):
    lower_bound: str = Field(min_length=1, max_length=300)
    upper_bound: str = Field(min_length=1, max_length=300)


class BackfillRequest(ActorRequest):
    partitions: list[BackfillPartitionRequest] = Field(min_length=1, max_length=1_000)


class BackfillResponse(BaseModel):
    partition_ids: list[UUID]


class PriorityRefreshResponse(BaseModel):
    job_id: UUID
    created: bool


class AdapterCapabilityResponse(BaseModel):
    adapter_id: str
    adapter_version: str
    provider_schema_version: str
    modes: list[str]
    canonical_output_types: list[str]
    supports_corrections: bool
    supports_tombstones: bool
    supports_retractions: bool
    max_page_size: int | None
    max_window_days: int | None
    cost_per_request: float

    @classmethod
    def from_domain(cls, value: AdapterCapabilityManifest) -> AdapterCapabilityResponse:
        return cls(
            adapter_id=value.adapter_id,
            adapter_version=value.adapter_version,
            provider_schema_version=value.provider_schema_version,
            modes=sorted(mode.value for mode in value.modes),
            canonical_output_types=list(value.canonical_output_types),
            supports_corrections=value.supports_corrections,
            supports_tombstones=value.supports_tombstones,
            supports_retractions=value.supports_retractions,
            max_page_size=value.max_page_size,
            max_window_days=value.max_window_days,
            cost_per_request=value.cost_per_request,
        )


class SourceHealthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    freshness_state: str
    schema_state: str
    volume_state: str
    field_population_state: str
    circuit_state: str
    last_attempt_at: datetime | None
    last_success_at: datetime | None
    last_source_record_at: datetime | None
    consecutive_failures: int
    quota_remaining: int | None
    monthly_cost_used: float
    cost_window_started_at: datetime | None
    current_backfill_state: str | None
    last_error_code: str | None

    @classmethod
    def from_domain(cls, value: SourceHealth) -> SourceHealthResponse:
        return cls(
            freshness_state=value.freshness_state.value,
            schema_state=value.schema_state.value,
            volume_state=value.volume_state.value,
            field_population_state=value.field_population_state.value,
            circuit_state=value.circuit_state,
            last_attempt_at=value.last_attempt_at,
            last_success_at=value.last_success_at,
            last_source_record_at=value.last_source_record_at,
            consecutive_failures=value.consecutive_failures,
            quota_remaining=value.quota_remaining,
            monthly_cost_used=value.monthly_cost_used,
            cost_window_started_at=value.cost_window_started_at,
            current_backfill_state=(
                value.current_backfill_state.value
                if value.current_backfill_state is not None
                else None
            ),
            last_error_code=value.last_error_code,
        )


class SourcePortfolioResponse(BaseModel):
    source_id: str
    display_name: str
    canonical_url: str
    category: str
    status: str
    executable: bool
    manual_resume_allowed: bool
    freshness_max_age_seconds: int
    commercial_use_cases: list[str]
    authorization_expires_at: datetime | None
    review_due_at: datetime | None
    candidate_origin: str | None
    monthly_cost_limit: float | None
    adapter: AdapterCapabilityResponse | None
    health: SourceHealthResponse

    @classmethod
    def from_domain(
        cls,
        entry: SourceCatalogEntry,
        health: SourceHealth,
    ) -> SourcePortfolioResponse:
        return cls(
            source_id=entry.source_id,
            display_name=entry.display_name,
            canonical_url=entry.canonical_url,
            category=entry.category,
            status=entry.status.value,
            executable=entry.executable,
            manual_resume_allowed="activation_requires" not in entry.metadata,
            freshness_max_age_seconds=entry.freshness_max_age_seconds,
            commercial_use_cases=list(entry.commercial_use_cases),
            authorization_expires_at=entry.authorization_expires_at,
            review_due_at=entry.review_due_at,
            candidate_origin=entry.candidate_origin,
            monthly_cost_limit=entry.monthly_cost_limit,
            adapter=(
                AdapterCapabilityResponse.from_domain(entry.adapter)
                if entry.adapter is not None
                else None
            ),
            health=SourceHealthResponse.from_domain(health),
        )


class SourcePortfolioPageResponse(BaseModel):
    items: list[SourcePortfolioResponse]
    total: int

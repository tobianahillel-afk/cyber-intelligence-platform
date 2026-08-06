from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PassiveAssetFilters:
    asset_kind: str | None = None
    state: str | None = None
    organization_link_status: str | None = None
    attribution_risk: str | None = None
    organization_id: UUID | None = None
    active: bool | None = None
    historical_only: bool | None = None
    has_conflict: bool | None = None
    query: str | None = None


@dataclass(frozen=True, slots=True)
class PassiveAssetSummary:
    id: UUID
    asset_key: str
    asset_kind: str
    asset_value: str
    state: str
    observed_states: tuple[str, ...]
    first_seen_at: datetime
    last_seen_at: datetime
    expires_at: datetime | None
    last_updated_at: datetime
    source_count: int
    independent_source_count: int
    active: bool
    historical_only: bool
    has_conflict: bool
    organization_link_status: str
    exact_organization_id: UUID | None
    candidate_organization_ids: tuple[UUID, ...]
    organization_link_reasons: tuple[str, ...]
    attribution_risks: tuple[str, ...]
    exposure_assessment: str = "not_assessed"


@dataclass(frozen=True, slots=True)
class PassiveAssetPage:
    items: tuple[PassiveAssetSummary, ...]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class PassiveTechnologyView:
    evidence_level: str
    product_name: str | None
    product_version: str | None
    component_name: str | None


@dataclass(frozen=True, slots=True)
class PassiveObservationView:
    id: UUID
    source_id: str
    source_record_key: str
    source_url: str
    observation_kind: str
    state: str
    observed_at: datetime
    published_at: datetime
    modified_at: datetime
    expires_at: datetime | None
    independence_key: str
    confidence: float
    organization_id: UUID | None
    organization_link_status: str
    organization_link_method: str
    organization_link_confidence: float
    organization_link_reasons: tuple[str, ...]
    attribution_risks: tuple[str, ...]
    port: int | None
    protocol: str | None
    active: bool
    historical_only: bool
    metadata_only: bool
    passive_only: bool
    supersedes_record_key: str | None
    technology: PassiveTechnologyView | None


@dataclass(frozen=True, slots=True)
class PassiveAssetDetail:
    asset: PassiveAssetSummary
    observations: tuple[PassiveObservationView, ...]
    safety_disclaimer: str = (
        "Passive provider metadata is not an active scan and does not prove "
        "vulnerability applicability, verified exposure, or compromise. "
        "Organization links remain reviewable when attribution is ambiguous."
    )

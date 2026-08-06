from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class IncidentFilters:
    status: str | None = None
    incident_type: str | None = None
    claim_type: str | None = None
    source_kind: str | None = None
    organization_link_status: str | None = None
    officially_confirmed: bool | None = None
    historical_only: bool | None = None
    query: str | None = None


@dataclass(frozen=True, slots=True)
class IncidentSummary:
    id: UUID
    incident_key: str
    incident_type: str
    title: str
    summary: str
    status: str
    organization_id: UUID | None
    organization_link_status: str
    occurrence_start_at: datetime | None
    occurrence_end_at: datetime | None
    discovered_at: datetime | None
    first_published_at: datetime
    confirmed_at: datetime | None
    last_updated_at: datetime
    claim_count: int
    independent_source_count: int
    officially_confirmed: bool
    has_denial: bool
    has_retraction: bool
    historical_only: bool


@dataclass(frozen=True, slots=True)
class IncidentPage:
    items: tuple[IncidentSummary, ...]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class IncidentClaimView:
    id: UUID
    source_id: str
    source_kind: str
    source_record_key: str
    source_url: str
    claim_type: str
    incident_type: str
    title: str
    summary: str
    claimed_organization_name: str | None
    organization_id: UUID | None
    organization_link_status: str
    published_at: datetime
    modified_at: datetime
    occurrence_start_at: datetime | None
    occurrence_end_at: datetime | None
    discovered_at: datetime | None
    confirmed_at: datetime | None
    independence_key: str
    confidence: float
    active: bool
    historical_only: bool
    metadata_only: bool
    supersedes_record_key: str | None


@dataclass(frozen=True, slots=True)
class IncidentDetail:
    incident: IncidentSummary
    claimed_organization_names: tuple[str, ...]
    claims: tuple[IncidentClaimView, ...]

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ChangeFilters:
    status: str | None = None
    event_type: str | None = None
    claim_type: str | None = None
    source_kind: str | None = None
    organization_link_status: str | None = None
    organization_id: UUID | None = None
    officially_confirmed: bool | None = None
    historical_only: bool | None = None
    query: str | None = None


@dataclass(frozen=True, slots=True)
class ChangeSummary:
    id: UUID
    event_key: str
    event_type: str
    title: str
    excerpt: str
    status: str
    organization_id: UUID | None
    organization_link_status: str
    event_at: datetime | None
    first_published_at: datetime
    last_updated_at: datetime
    claim_count: int
    independent_source_count: int
    officially_confirmed: bool
    has_dispute: bool
    has_correction: bool
    has_retraction: bool
    historical_only: bool


@dataclass(frozen=True, slots=True)
class ChangePage:
    items: tuple[ChangeSummary, ...]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class ChangeClaimView:
    id: UUID
    source_id: str
    source_kind: str
    source_record_key: str
    article_id: str
    source_url: str
    claim_type: str
    title: str
    excerpt: str
    claimed_organization_name: str | None
    organization_id: UUID | None
    organization_link_status: str
    published_at: datetime
    modified_at: datetime
    event_at: datetime | None
    expires_at: datetime | None
    independence_key: str
    syndication_group_key: str | None
    confidence: float
    active: bool
    historical_only: bool
    supersedes_record_key: str | None


@dataclass(frozen=True, slots=True)
class ChangeServiceMappingView:
    id: UUID
    service_family: str
    rationale: str
    confidence: float
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ChangeDetail:
    event: ChangeSummary
    claimed_organization_names: tuple[str, ...]
    claims: tuple[ChangeClaimView, ...]
    service_mappings: tuple[ChangeServiceMappingView, ...]

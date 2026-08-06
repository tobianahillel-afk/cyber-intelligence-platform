from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from cip.modules.public_footprint.domain.models import (
    PublicClaimType,
    PublicResourceKind,
    ResourceAccessState,
    ResourceRetrievalState,
)


@dataclass(frozen=True, slots=True)
class PublicResourceFilters:
    organization_id: UUID | None = None
    source_id: str | None = None
    kind: PublicResourceKind | None = None
    access_state: ResourceAccessState | None = None
    retrieval_state: ResourceRetrievalState | None = None
    claim_type: PublicClaimType | None = None
    query: str | None = None


@dataclass(frozen=True, slots=True)
class PublicClaimItem:
    id: UUID
    resource_version_id: UUID
    claim_type: str
    statement: str
    evidence_basis: str
    resolution_status: str
    confidence: float
    corroboration_group_key: str
    source_locator: str | None
    excerpt: str | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PublicResourceVersionItem:
    id: UUID
    source_url: str
    content_hash_sha256: str
    fetched_at: datetime
    published_at: datetime | None
    source_updated_at: datetime | None
    mime_type: str
    byte_size: int
    title: str | None
    language: str | None
    extracted_text_hash_sha256: str | None
    excerpt: str | None
    source_locator: str | None
    supersedes_version_id: UUID | None


@dataclass(frozen=True, slots=True)
class PublicResourceListItem:
    id: UUID
    organization_id: UUID
    organization_name: str
    source_id: str
    source_record_key: str
    canonical_url: str
    source_url: str
    kind: str
    discovery_method: str
    access_state: str
    retrieval_state: str
    title: str | None
    first_discovered_at: datetime
    last_seen_at: datetime
    latest_version_id: UUID | None
    latest_fetched_at: datetime | None
    latest_mime_type: str | None
    latest_excerpt: str | None
    version_count: int
    claim_count: int
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PublicResourcePage:
    items: tuple[PublicResourceListItem, ...]
    total: int
    limit: int
    offset: int
    generated_at: datetime


@dataclass(frozen=True, slots=True)
class PublicResourceDetail:
    resource: PublicResourceListItem
    identity_key: str
    corroboration_group_key: str
    versions: tuple[PublicResourceVersionItem, ...]
    claims: tuple[PublicClaimItem, ...]

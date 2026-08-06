from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from cip.modules.public_footprint.application.view_models import (
    PublicResourceDetail,
    PublicResourcePage,
)


class PublicResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class PublicResourcePageResponse(BaseModel):
    items: tuple[PublicResourceResponse, ...]
    total: int
    limit: int
    offset: int
    generated_at: datetime

    @classmethod
    def from_domain(cls, page: PublicResourcePage) -> Self:
        return cls(
            items=tuple(PublicResourceResponse.model_validate(item) for item in page.items),
            total=page.total,
            limit=page.limit,
            offset=page.offset,
            generated_at=page.generated_at,
        )


class PublicResourceVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class PublicClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class PublicResourceDetailResponse(BaseModel):
    resource: PublicResourceResponse
    identity_key: str
    corroboration_group_key: str
    versions: tuple[PublicResourceVersionResponse, ...]
    claims: tuple[PublicClaimResponse, ...]

    @classmethod
    def from_domain(cls, detail: PublicResourceDetail) -> Self:
        return cls(
            resource=PublicResourceResponse.model_validate(detail.resource),
            identity_key=detail.identity_key,
            corroboration_group_key=detail.corroboration_group_key,
            versions=tuple(
                PublicResourceVersionResponse.model_validate(item)
                for item in detail.versions
            ),
            claims=tuple(PublicClaimResponse.model_validate(item) for item in detail.claims),
        )

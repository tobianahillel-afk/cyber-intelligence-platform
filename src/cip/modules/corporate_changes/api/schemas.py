from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from cip.modules.corporate_changes.application.view_models import (
    ChangeClaimView,
    ChangeDetail,
    ChangePage,
    ChangeServiceMappingView,
    ChangeSummary,
)


class ChangeSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    claim_count: int = Field(ge=1)
    independent_source_count: int = Field(ge=0)
    officially_confirmed: bool
    has_dispute: bool
    has_correction: bool
    has_retraction: bool
    historical_only: bool

    @classmethod
    def from_domain(cls, item: ChangeSummary) -> ChangeSummaryResponse:
        return cls(
            id=item.id,
            event_key=item.event_key,
            event_type=item.event_type,
            title=item.title,
            excerpt=item.excerpt,
            status=item.status,
            organization_id=item.organization_id,
            organization_link_status=item.organization_link_status,
            event_at=item.event_at,
            first_published_at=item.first_published_at,
            last_updated_at=item.last_updated_at,
            claim_count=item.claim_count,
            independent_source_count=item.independent_source_count,
            officially_confirmed=item.officially_confirmed,
            has_dispute=item.has_dispute,
            has_correction=item.has_correction,
            has_retraction=item.has_retraction,
            historical_only=item.historical_only,
        )


class ChangePageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ChangeSummaryResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)

    @classmethod
    def from_domain(cls, page: ChangePage) -> ChangePageResponse:
        return cls(
            items=[ChangeSummaryResponse.from_domain(item) for item in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )


class ChangeClaimResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    confidence: float = Field(ge=0, le=1)
    active: bool
    historical_only: bool
    supersedes_record_key: str | None

    @classmethod
    def from_domain(cls, item: ChangeClaimView) -> ChangeClaimResponse:
        return cls(
            id=item.id,
            source_id=item.source_id,
            source_kind=item.source_kind,
            source_record_key=item.source_record_key,
            article_id=item.article_id,
            source_url=item.source_url,
            claim_type=item.claim_type,
            title=item.title,
            excerpt=item.excerpt,
            claimed_organization_name=item.claimed_organization_name,
            organization_id=item.organization_id,
            organization_link_status=item.organization_link_status,
            published_at=item.published_at,
            modified_at=item.modified_at,
            event_at=item.event_at,
            expires_at=item.expires_at,
            independence_key=item.independence_key,
            syndication_group_key=item.syndication_group_key,
            confidence=item.confidence,
            active=item.active,
            historical_only=item.historical_only,
            supersedes_record_key=item.supersedes_record_key,
        )


class ChangeServiceMappingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    service_family: str
    rationale: str
    confidence: float = Field(ge=0, le=1)
    created_at: datetime

    @classmethod
    def from_domain(
        cls,
        item: ChangeServiceMappingView,
    ) -> ChangeServiceMappingResponse:
        return cls(
            id=item.id,
            service_family=item.service_family,
            rationale=item.rationale,
            confidence=item.confidence,
            created_at=item.created_at,
        )


class ChangeDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: ChangeSummaryResponse
    claimed_organization_names: list[str]
    claims: list[ChangeClaimResponse]
    service_mappings: list[ChangeServiceMappingResponse]
    evidence_disclaimer: str

    @classmethod
    def from_domain(cls, detail: ChangeDetail) -> ChangeDetailResponse:
        return cls(
            event=ChangeSummaryResponse.from_domain(detail.event),
            claimed_organization_names=list(detail.claimed_organization_names),
            claims=[ChangeClaimResponse.from_domain(item) for item in detail.claims],
            service_mappings=[
                ChangeServiceMappingResponse.from_domain(item)
                for item in detail.service_mappings
            ],
            evidence_disclaimer=(
                "Corporate-change intelligence contains public or licensed metadata. "
                "Reporting and speculation are not official confirmation, syndicated "
                "copies are not independent corroboration, and service mappings remain "
                "separate from raw change evidence."
            ),
        )

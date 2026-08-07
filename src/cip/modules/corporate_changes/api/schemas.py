from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from cip.modules.corporate_changes.application.view_models import (
    ChangeClaimView,
    ChangeDetail,
    ChangePage,
    ChangeServiceMappingView,
    ChangeSummary,
)


class ChangeSummaryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

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

    @classmethod
    def from_domain(cls, value: ChangeSummary) -> ChangeSummaryResponse:
        return cls(**value.__dict__)


class ChangePageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: tuple[ChangeSummaryResponse, ...]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_domain(cls, value: ChangePage) -> ChangePageResponse:
        return cls(
            items=tuple(ChangeSummaryResponse.from_domain(item) for item in value.items),
            total=value.total,
            limit=value.limit,
            offset=value.offset,
        )


class ChangeClaimResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

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

    @classmethod
    def from_domain(cls, value: ChangeClaimView) -> ChangeClaimResponse:
        return cls(**value.__dict__)


class ChangeServiceMappingResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    service_family: str
    rationale: str
    confidence: float
    created_at: datetime

    @classmethod
    def from_domain(
        cls,
        value: ChangeServiceMappingView,
    ) -> ChangeServiceMappingResponse:
        return cls(**value.__dict__)


class ChangeDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    event: ChangeSummaryResponse
    claimed_organization_names: tuple[str, ...]
    claims: tuple[ChangeClaimResponse, ...]
    service_mappings: tuple[ChangeServiceMappingResponse, ...]

    @classmethod
    def from_domain(cls, value: ChangeDetail) -> ChangeDetailResponse:
        return cls(
            event=ChangeSummaryResponse.from_domain(value.event),
            claimed_organization_names=value.claimed_organization_names,
            claims=tuple(ChangeClaimResponse.from_domain(item) for item in value.claims),
            service_mappings=tuple(
                ChangeServiceMappingResponse.from_domain(item)
                for item in value.service_mappings
            ),
        )

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from cip.modules.incident_intelligence.application.view_models import (
    IncidentClaimView,
    IncidentDetail,
    IncidentPage,
    IncidentSummary,
)


class IncidentSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    claim_count: int = Field(ge=1)
    independent_source_count: int = Field(ge=0)
    officially_confirmed: bool
    has_denial: bool
    has_retraction: bool
    historical_only: bool

    @classmethod
    def from_domain(cls, item: IncidentSummary) -> IncidentSummaryResponse:
        return cls(
            id=item.id,
            incident_key=item.incident_key,
            incident_type=item.incident_type,
            title=item.title,
            summary=item.summary,
            status=item.status,
            organization_id=item.organization_id,
            organization_link_status=item.organization_link_status,
            occurrence_start_at=item.occurrence_start_at,
            occurrence_end_at=item.occurrence_end_at,
            discovered_at=item.discovered_at,
            first_published_at=item.first_published_at,
            confirmed_at=item.confirmed_at,
            last_updated_at=item.last_updated_at,
            claim_count=item.claim_count,
            independent_source_count=item.independent_source_count,
            officially_confirmed=item.officially_confirmed,
            has_denial=item.has_denial,
            has_retraction=item.has_retraction,
            historical_only=item.historical_only,
        )


class IncidentPageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[IncidentSummaryResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)

    @classmethod
    def from_domain(cls, page: IncidentPage) -> IncidentPageResponse:
        return cls(
            items=[IncidentSummaryResponse.from_domain(item) for item in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )


class IncidentClaimResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    confidence: float = Field(ge=0, le=1)
    active: bool
    historical_only: bool
    metadata_only: bool
    supersedes_record_key: str | None

    @classmethod
    def from_domain(cls, item: IncidentClaimView) -> IncidentClaimResponse:
        return cls(
            id=item.id,
            source_id=item.source_id,
            source_kind=item.source_kind,
            source_record_key=item.source_record_key,
            source_url=item.source_url,
            claim_type=item.claim_type,
            incident_type=item.incident_type,
            title=item.title,
            summary=item.summary,
            claimed_organization_name=item.claimed_organization_name,
            organization_id=item.organization_id,
            organization_link_status=item.organization_link_status,
            published_at=item.published_at,
            modified_at=item.modified_at,
            occurrence_start_at=item.occurrence_start_at,
            occurrence_end_at=item.occurrence_end_at,
            discovered_at=item.discovered_at,
            confirmed_at=item.confirmed_at,
            independence_key=item.independence_key,
            confidence=item.confidence,
            active=item.active,
            historical_only=item.historical_only,
            metadata_only=item.metadata_only,
            supersedes_record_key=item.supersedes_record_key,
        )


class IncidentDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident: IncidentSummaryResponse
    claimed_organization_names: list[str]
    claims: list[IncidentClaimResponse]
    safety_disclaimer: str

    @classmethod
    def from_domain(cls, detail: IncidentDetail) -> IncidentDetailResponse:
        return cls(
            incident=IncidentSummaryResponse.from_domain(detail.incident),
            claimed_organization_names=list(detail.claimed_organization_names),
            claims=[IncidentClaimResponse.from_domain(item) for item in detail.claims],
            safety_disclaimer=(
                "Incident intelligence contains public metadata and source claims only. "
                "An allegation is not an official confirmation, and the platform never "
                "collects victim files, stolen data, credentials, private communications, "
                "or threat-actor negotiation content."
            ),
        )

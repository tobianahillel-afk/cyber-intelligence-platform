from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from cip.modules.passive_exposure.application.view_models import (
    PassiveAssetDetail,
    PassiveAssetPage,
    PassiveAssetSummary,
    PassiveObservationView,
    PassiveTechnologyView,
)


class PassiveAssetSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    exposure_assessment: str

    @classmethod
    def from_domain(cls, value: PassiveAssetSummary) -> PassiveAssetSummaryResponse:
        return cls.model_validate(value)


class PassiveTechnologyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_level: str
    product_name: str | None
    product_version: str | None
    component_name: str | None

    @classmethod
    def from_domain(cls, value: PassiveTechnologyView) -> PassiveTechnologyResponse:
        return cls.model_validate(value)


class PassiveObservationResponse(BaseModel):
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
    technology: PassiveTechnologyResponse | None

    @classmethod
    def from_domain(cls, value: PassiveObservationView) -> PassiveObservationResponse:
        technology = (
            PassiveTechnologyResponse.from_domain(value.technology)
            if value.technology is not None
            else None
        )
        return cls(
            id=value.id,
            source_id=value.source_id,
            source_record_key=value.source_record_key,
            source_url=value.source_url,
            observation_kind=value.observation_kind,
            state=value.state,
            observed_at=value.observed_at,
            published_at=value.published_at,
            modified_at=value.modified_at,
            expires_at=value.expires_at,
            independence_key=value.independence_key,
            confidence=value.confidence,
            organization_id=value.organization_id,
            organization_link_status=value.organization_link_status,
            organization_link_method=value.organization_link_method,
            organization_link_confidence=value.organization_link_confidence,
            organization_link_reasons=value.organization_link_reasons,
            attribution_risks=value.attribution_risks,
            port=value.port,
            protocol=value.protocol,
            active=value.active,
            historical_only=value.historical_only,
            metadata_only=value.metadata_only,
            passive_only=value.passive_only,
            supersedes_record_key=value.supersedes_record_key,
            technology=technology,
        )


class PassiveAssetPageResponse(BaseModel):
    items: tuple[PassiveAssetSummaryResponse, ...]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_domain(cls, value: PassiveAssetPage) -> PassiveAssetPageResponse:
        return cls(
            items=tuple(
                PassiveAssetSummaryResponse.from_domain(item) for item in value.items
            ),
            total=value.total,
            limit=value.limit,
            offset=value.offset,
        )


class PassiveAssetDetailResponse(BaseModel):
    asset: PassiveAssetSummaryResponse
    observations: tuple[PassiveObservationResponse, ...]
    safety_disclaimer: str

    @classmethod
    def from_domain(cls, value: PassiveAssetDetail) -> PassiveAssetDetailResponse:
        return cls(
            asset=PassiveAssetSummaryResponse.from_domain(value.asset),
            observations=tuple(
                PassiveObservationResponse.from_domain(observation)
                for observation in value.observations
            ),
            safety_disclaimer=value.safety_disclaimer,
        )

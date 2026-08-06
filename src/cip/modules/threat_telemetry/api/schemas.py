from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from cip.modules.threat_telemetry.application.view_models import (
    IndicatorDetail,
    IndicatorPage,
    IndicatorRelationView,
    IndicatorSnapshotView,
    IndicatorSummary,
)


class IndicatorSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    indicator_key: str
    indicator_type: str
    indicator_value: str
    state: str
    observed_states: tuple[str, ...]
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    expires_at: datetime | None
    last_updated_at: datetime
    source_count: int
    independent_source_count: int
    active: bool
    shared_infrastructure: bool
    historical_only: bool
    has_conflict: bool

    @classmethod
    def from_domain(cls, value: IndicatorSummary) -> IndicatorSummaryResponse:
        return cls.model_validate(value)


class IndicatorRelationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    relation_type: str
    target_key: str
    confidence: float

    @classmethod
    def from_domain(cls, value: IndicatorRelationView) -> IndicatorRelationResponse:
        return cls.model_validate(value)


class IndicatorSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: str
    source_kind: str
    source_record_key: str
    source_url: str
    state: str
    published_at: datetime
    modified_at: datetime
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    expires_at: datetime | None
    independence_key: str
    sensor_scope: str
    confidence: float
    source_precedence: int
    active: bool
    shared_infrastructure: bool
    historical_only: bool
    metadata_only: bool
    supersedes_record_key: str | None
    relations: tuple[IndicatorRelationResponse, ...]

    @classmethod
    def from_domain(cls, value: IndicatorSnapshotView) -> IndicatorSnapshotResponse:
        return cls(
            id=value.id,
            source_id=value.source_id,
            source_kind=value.source_kind,
            source_record_key=value.source_record_key,
            source_url=value.source_url,
            state=value.state,
            published_at=value.published_at,
            modified_at=value.modified_at,
            first_seen_at=value.first_seen_at,
            last_seen_at=value.last_seen_at,
            expires_at=value.expires_at,
            independence_key=value.independence_key,
            sensor_scope=value.sensor_scope,
            confidence=value.confidence,
            source_precedence=value.source_precedence,
            active=value.active,
            shared_infrastructure=value.shared_infrastructure,
            historical_only=value.historical_only,
            metadata_only=value.metadata_only,
            supersedes_record_key=value.supersedes_record_key,
            relations=tuple(
                IndicatorRelationResponse.from_domain(relation)
                for relation in value.relations
            ),
        )


class IndicatorPageResponse(BaseModel):
    items: tuple[IndicatorSummaryResponse, ...]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_domain(cls, value: IndicatorPage) -> IndicatorPageResponse:
        return cls(
            items=tuple(
                IndicatorSummaryResponse.from_domain(item) for item in value.items
            ),
            total=value.total,
            limit=value.limit,
            offset=value.offset,
        )


class IndicatorDetailResponse(BaseModel):
    indicator: IndicatorSummaryResponse
    snapshots: tuple[IndicatorSnapshotResponse, ...]
    safety_disclaimer: str

    @classmethod
    def from_domain(cls, value: IndicatorDetail) -> IndicatorDetailResponse:
        return cls(
            indicator=IndicatorSummaryResponse.from_domain(value.indicator),
            snapshots=tuple(
                IndicatorSnapshotResponse.from_domain(snapshot)
                for snapshot in value.snapshots
            ),
            safety_disclaimer=value.safety_disclaimer,
        )

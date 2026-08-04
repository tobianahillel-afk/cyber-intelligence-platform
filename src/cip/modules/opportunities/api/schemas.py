from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cip.modules.opportunities.application.view_models import (
    OpportunityDetail,
    OpportunityPage,
)
from cip.modules.opportunities.domain.entities import (
    OpportunityFamily,
    OpportunityState,
    ReviewAction,
)


class OpportunityListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    organization: str
    country: str | None
    family: str
    state: str
    data_quality: str
    recommended_offer: str
    score: float
    confidence: float
    trigger: str
    last_evidence_at: datetime
    updated_at: datetime
    relevant_roles: tuple[str, ...]
    next_action: str
    evidence_count: int
    snoozed_until: datetime | None


class OpportunityPageResponse(BaseModel):
    items: tuple[OpportunityListItemResponse, ...]
    total: int
    limit: int
    offset: int
    generated_at: datetime

    @classmethod
    def from_domain(cls, page: OpportunityPage) -> OpportunityPageResponse:
        return cls(
            items=tuple(
                OpportunityListItemResponse.model_validate(item) for item in page.items
            ),
            total=page.total,
            limit=page.limit,
            offset=page.offset,
            generated_at=page.generated_at,
        )


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: str
    source_url: str
    source_record_key: str | None
    summary: str
    confidence: float
    collected_at: datetime
    published_at: datetime | None
    observed_at: datetime | None


class ScoreComponentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule_id: str
    value: float
    weight: float
    contribution: float
    kind: str
    reason: str
    evidence_ids: tuple[UUID, ...]
    analyst_overridden: bool
    original_value: float | None
    original_weight: float | None


class ReviewHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action: str
    previous_state: str
    new_state: str
    actor: str
    note: str | None
    occurred_at: datetime
    snoozed_until: datetime | None


class OpportunityDetailResponse(BaseModel):
    opportunity: OpportunityListItemResponse
    hypothesis_id: UUID
    hypothesis_status: str
    rule_id: str
    rule_version: str
    rationale: str
    generated_at: datetime
    expires_at: datetime | None
    score_version: str
    config_version: str
    raw_score: float
    calculation_hash: str
    review_note: str | None
    rejected_reason: str | None
    components: tuple[ScoreComponentResponse, ...]
    evidence: tuple[EvidenceResponse, ...]
    reviews: tuple[ReviewHistoryResponse, ...]

    @classmethod
    def from_domain(cls, detail: OpportunityDetail) -> OpportunityDetailResponse:
        return cls(
            opportunity=OpportunityListItemResponse.model_validate(detail.opportunity),
            hypothesis_id=detail.hypothesis_id,
            hypothesis_status=detail.hypothesis_status,
            rule_id=detail.rule_id,
            rule_version=detail.rule_version,
            rationale=detail.rationale,
            generated_at=detail.generated_at,
            expires_at=detail.expires_at,
            score_version=detail.score_version,
            config_version=detail.config_version,
            raw_score=detail.raw_score,
            calculation_hash=detail.calculation_hash,
            review_note=detail.review_note,
            rejected_reason=detail.rejected_reason,
            components=tuple(
                ScoreComponentResponse.model_validate(item) for item in detail.components
            ),
            evidence=tuple(EvidenceResponse.model_validate(item) for item in detail.evidence),
            reviews=tuple(
                ReviewHistoryResponse.model_validate(item) for item in detail.reviews
            ),
        )


class OpportunityFilters(BaseModel):
    states: tuple[OpportunityState, ...] = ()
    family: OpportunityFamily | None = None
    min_score: float = Field(default=0.0, ge=0.0, le=100.0)
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class ReviewRequest(BaseModel):
    action: ReviewAction
    actor: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=4_000)
    snoozed_until: datetime | None = None

    @field_validator("actor")
    @classmethod
    def normalize_actor(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("actor is required")
        return normalized

    @field_validator("snoozed_until")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("snoozed_until must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_action_fields(self) -> Self:
        if self.action is ReviewAction.REJECT and not (self.note and self.note.strip()):
            raise ValueError("reject requires a reason")
        if self.action is ReviewAction.SNOOZE and self.snoozed_until is None:
            raise ValueError("snooze requires snoozed_until")
        return self


class ReviewResponse(BaseModel):
    id: UUID
    state: OpportunityState


class ScoreComponentOverrideRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=200)
    value: float | None = Field(default=None, ge=0.0, le=1.0)
    weight: float | None = Field(default=None, ge=0.0, le=100.0)
    reason: str | None = Field(default=None, max_length=4_000)

    @field_validator("actor")
    @classmethod
    def normalize_actor(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("actor is required")
        return normalized

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("reason cannot be empty")
        return normalized

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if self.value is None and self.weight is None and self.reason is None:
            raise ValueError("at least one component field must change")
        return self


class ScoreComponentOverrideResponse(BaseModel):
    opportunity_id: UUID
    component_id: UUID
    score: float

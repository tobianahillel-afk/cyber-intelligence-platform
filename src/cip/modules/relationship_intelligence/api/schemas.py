from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from cip.modules.relationship_intelligence.application.view_models import (
    RelationshipContextView,
    RelationshipDetail,
    RelationshipEvidenceView,
    RelationshipPage,
    RelationshipSummary,
)


class RelationshipSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    relationship_key: str
    role: str
    status: str
    source_organization_id: UUID | None
    target_organization_id: UUID | None
    source_link_status: str
    target_link_status: str
    source_name: str | None
    target_name: str | None
    valid_from: datetime | None
    valid_until: datetime | None
    first_published_at: datetime
    last_updated_at: datetime
    last_observed_at: datetime
    evidence_count: int = Field(ge=1)
    independent_source_count: int = Field(ge=0)
    strongest_evidence_class: str
    confidence: float = Field(ge=0, le=1)
    has_contract_evidence: bool
    contract_backed_current: bool
    next_renewal_at: datetime | None
    has_role_conflict: bool
    has_dispute: bool
    has_correction: bool
    has_retraction: bool
    historical_only: bool

    @classmethod
    def from_domain(cls, item: RelationshipSummary) -> RelationshipSummaryResponse:
        return cls(**asdict(item))


class RelationshipPageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[RelationshipSummaryResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)

    @classmethod
    def from_domain(cls, page: RelationshipPage) -> RelationshipPageResponse:
        return cls(
            items=[RelationshipSummaryResponse.from_domain(item) for item in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )


class RelationshipEvidenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    source_id: str
    source_kind: str
    source_record_key: str
    source_url: str
    claim_type: str
    role: str
    evidence_class: str
    title: str
    excerpt: str
    claimed_source_organization_name: str | None
    claimed_target_organization_name: str | None
    source_organization_id: UUID | None
    target_organization_id: UUID | None
    source_link_status: str
    target_link_status: str
    published_at: datetime
    modified_at: datetime
    observed_at: datetime
    valid_from: datetime | None
    valid_until: datetime | None
    expires_at: datetime | None
    contract_reference: str | None
    product_context: str | None
    service_context: str | None
    renewal_at: datetime | None
    independence_key: str
    confidence: float = Field(ge=0, le=1)
    active: bool
    historical_only: bool
    supersedes_record_key: str | None

    @classmethod
    def from_domain(
        cls,
        item: RelationshipEvidenceView,
    ) -> RelationshipEvidenceResponse:
        return cls(**asdict(item))


class RelationshipContextResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    context_type: str
    value: str
    reference: str | None
    confidence: float = Field(ge=0, le=1)
    created_at: datetime

    @classmethod
    def from_domain(cls, item: RelationshipContextView) -> RelationshipContextResponse:
        return cls(**asdict(item))


class RelationshipDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relationship: RelationshipSummaryResponse
    claimed_source_organization_names: list[str]
    claimed_target_organization_names: list[str]
    evidence: list[RelationshipEvidenceResponse]
    contexts: list[RelationshipContextResponse]
    evidence_disclaimer: str

    @classmethod
    def from_domain(cls, detail: RelationshipDetail) -> RelationshipDetailResponse:
        return cls(
            relationship=RelationshipSummaryResponse.from_domain(detail.relationship),
            claimed_source_organization_names=list(
                detail.claimed_source_organization_names
            ),
            claimed_target_organization_names=list(
                detail.claimed_target_organization_names
            ),
            evidence=[
                RelationshipEvidenceResponse.from_domain(item)
                for item in detail.evidence
            ],
            contexts=[
                RelationshipContextResponse.from_domain(item)
                for item in detail.contexts
            ],
            evidence_disclaimer=(
                "Relationship evidence preserves direction, chronology, evidence class, "
                "and review state. Marketing claims are not contract evidence, historical "
                "or inferred relationships are not current incumbents, and relationship "
                "evidence is not a service need, opportunity, or contact authorization."
            ),
        )

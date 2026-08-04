from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from cip.modules.organizations.application.identity_views import (
    AliasView,
    IdentifierView,
    IdentityClaimView,
    IdentityView,
    MergeCandidatePage,
    MergeCandidateView,
    RelationshipView,
)
from cip.modules.organizations.domain.identity import MatchState


class IdentifierResponse(BaseModel):
    scheme: str
    value: str
    issuing_country: str | None
    source_id: str
    verified_at: datetime
    is_current: bool

    @classmethod
    def from_domain(cls, item: IdentifierView) -> IdentifierResponse:
        return cls(
            scheme=item.scheme.value,
            value=item.value,
            issuing_country=item.issuing_country,
            source_id=item.source_id,
            verified_at=item.verified_at,
            is_current=item.is_current,
        )


class AliasResponse(BaseModel):
    value: str
    source_id: str
    observed_at: datetime

    @classmethod
    def from_domain(cls, item: AliasView) -> AliasResponse:
        return cls(
            value=item.value,
            source_id=item.source_id,
            observed_at=item.observed_at,
        )


class RelationshipResponse(BaseModel):
    id: UUID
    subject_identity_id: UUID
    object_identity_id: UUID
    relationship_type: str
    source_id: str
    source_url: str
    confidence: float
    observed_at: datetime
    valid_from: date | None
    valid_until: date | None

    @classmethod
    def from_domain(cls, item: RelationshipView) -> RelationshipResponse:
        return cls(
            id=item.id,
            subject_identity_id=item.subject_identity_id,
            object_identity_id=item.object_identity_id,
            relationship_type=item.relationship_type.value,
            source_id=item.source_id,
            source_url=item.source_url,
            confidence=item.confidence,
            observed_at=item.observed_at,
            valid_from=item.valid_from,
            valid_until=item.valid_until,
        )


class IdentityClaimResponse(BaseModel):
    id: UUID
    source_id: str
    source_record_key: str
    source_url: str
    selected_fields: dict[str, object]
    confidence: float
    observed_at: datetime
    content_hash_sha256: str | None
    conflict_fields: list[str]

    @classmethod
    def from_domain(cls, item: IdentityClaimView) -> IdentityClaimResponse:
        return cls(
            id=item.id,
            source_id=item.source_id,
            source_record_key=item.source_record_key,
            source_url=item.source_url,
            selected_fields=dict(item.selected_fields),
            confidence=item.confidence,
            observed_at=item.observed_at,
            content_hash_sha256=item.content_hash_sha256,
            conflict_fields=list(item.conflict_fields),
        )


class IdentityResponse(BaseModel):
    id: UUID
    organization_id: UUID | None
    kind: str
    official_name: str
    country_code: str
    status: str
    legal_form: str | None
    activity_code: str | None
    address: str | None
    postal_code: str | None
    city: str | None
    is_headquarters: bool
    source_id: str
    source_record_key: str
    source_url: str
    confidence: float
    observed_at: datetime
    valid_from: date | None
    valid_until: date | None
    identifiers: list[IdentifierResponse]
    aliases: list[AliasResponse]
    evidence_ids: list[UUID]
    relationships: list[RelationshipResponse]
    claims: list[IdentityClaimResponse]
    conflict_fields: list[str]

    @classmethod
    def from_domain(cls, item: IdentityView) -> IdentityResponse:
        return cls(
            id=item.id,
            organization_id=item.organization_id,
            kind=item.kind.value,
            official_name=item.official_name,
            country_code=item.country_code,
            status=item.status.value,
            legal_form=item.legal_form,
            activity_code=item.activity_code,
            address=item.address,
            postal_code=item.postal_code,
            city=item.city,
            is_headquarters=item.is_headquarters,
            source_id=item.source_id,
            source_record_key=item.source_record_key,
            source_url=item.source_url,
            confidence=item.confidence,
            observed_at=item.observed_at,
            valid_from=item.valid_from,
            valid_until=item.valid_until,
            identifiers=[IdentifierResponse.from_domain(value) for value in item.identifiers],
            aliases=[AliasResponse.from_domain(value) for value in item.aliases],
            evidence_ids=list(item.evidence_ids),
            relationships=[RelationshipResponse.from_domain(value) for value in item.relationships],
            claims=[IdentityClaimResponse.from_domain(value) for value in item.claims],
            conflict_fields=list(item.conflict_fields),
        )


class MergeCandidateResponse(BaseModel):
    id: UUID
    identity_id: UUID
    organization_id: UUID
    organization_name: str
    identity_name: str
    method: str
    score: float
    reasons: list[str]
    state: str
    created_at: datetime
    reviewed_at: datetime | None
    reviewed_by: str | None
    review_note: str | None

    @classmethod
    def from_domain(cls, item: MergeCandidateView) -> MergeCandidateResponse:
        return cls(
            id=item.id,
            identity_id=item.identity_id,
            organization_id=item.organization_id,
            organization_name=item.organization_name,
            identity_name=item.identity_name,
            method=item.method.value,
            score=item.score,
            reasons=list(item.reasons),
            state=item.state.value,
            created_at=item.created_at,
            reviewed_at=item.reviewed_at,
            reviewed_by=item.reviewed_by,
            review_note=item.review_note,
        )


class MergeCandidatePageResponse(BaseModel):
    items: list[MergeCandidateResponse]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_domain(cls, page: MergeCandidatePage) -> MergeCandidatePageResponse:
        return cls(
            items=[MergeCandidateResponse.from_domain(item) for item in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )


class MergeCandidateReviewRequest(BaseModel):
    action: Literal["confirm", "reject"]
    actor: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=4_000)

    @field_validator("actor")
    @classmethod
    def normalize_actor(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("actor is required")
        return normalized


class MergeCandidateReviewResponse(BaseModel):
    id: UUID
    state: MatchState

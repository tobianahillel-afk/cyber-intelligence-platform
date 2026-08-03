from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import AnyHttpUrl, BaseModel, Field


class ClaimType(StrEnum):
    ACTOR_CLAIM = "actor_claim"
    MEDIA_REPORT = "media_report"
    OFFICIAL_STATEMENT = "official_statement"
    AUTHORITY_NOTICE = "authority_notice"
    ANALYST_INFERENCE = "analyst_inference"
    CORRECTION = "correction"
    DENIAL = "denial"


class VerificationStatus(StrEnum):
    UNVERIFIED = "unverified"
    PARTIALLY_CORROBORATED = "partially_corroborated"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    RETRACTED = "retracted"


class Organization(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    canonical_name: str = Field(min_length=1, max_length=300)
    legal_name: str | None = Field(default=None, max_length=300)
    country_code: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    website_url: AnyHttpUrl | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Evidence(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source_id: str
    source_url: AnyHttpUrl
    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    published_at: datetime | None = None
    summary: str = Field(min_length=1, max_length=4_000)
    confidence: float = Field(ge=0.0, le=1.0)
    raw_storage_permitted: bool = False


class EventClaim(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    organization_id: UUID | None = None
    claim_type: ClaimType
    claimant_name: str = Field(min_length=1, max_length=300)
    statement_summary: str = Field(min_length=1, max_length=4_000)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    evidence_id: UUID


class OpportunityComponent(BaseModel):
    component_type: str = Field(min_length=1, max_length=100)
    value: float
    weight: float
    contribution: float
    reason: str = Field(min_length=1, max_length=1_000)
    evidence_ids: list[UUID] = Field(default_factory=list)


class OpportunityScore(BaseModel):
    organization_id: UUID
    score: float = Field(ge=0.0, le=100.0)
    score_version: str = Field(min_length=1, max_length=50)
    components: list[OpportunityComponent]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

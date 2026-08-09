from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from cip.modules.professional_context.application.view_models import (
    CommunityContextView,
    OrganizationProfessionalMap,
    ProfessionalContactView,
    ProfessionalEvidenceView,
    ProfessionalPersonDetail,
    ProfessionalPersonPage,
    ProfessionalPersonSummary,
    ProfessionalRoleView,
    ReportingLineView,
    ServiceRelevanceView,
)


class ProfessionalPersonResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_key: str
    display_name: str | None
    confidence: float = Field(ge=0, le=1)
    review_state: str
    lawful_basis: str
    processing_purpose: str
    current: bool
    suppressed: bool
    deleted: bool
    last_observed_at: datetime
    retention_until: datetime
    current_role: str | None
    current_team: str | None
    organization_id: UUID | None

    @classmethod
    def from_domain(cls, item: ProfessionalPersonSummary) -> ProfessionalPersonResponse:
        return cls(**asdict(item))


class ProfessionalRoleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_key: str
    role_title: str | None
    team_name: str | None
    organization_id: UUID | None
    claimed_organization_name: str | None
    employment_state: str
    confidence: float = Field(ge=0, le=1)
    review_state: str
    first_observed_at: datetime
    last_observed_at: datetime
    retention_until: datetime
    suppressed: bool
    deleted: bool

    @classmethod
    def from_domain(cls, item: ProfessionalRoleView) -> ProfessionalRoleResponse:
        return cls(**asdict(item))


class ReportingLineResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_key: str
    subject_person_key: str
    manager_person_key: str
    organization_id: UUID | None
    confidence: float = Field(ge=0, le=1)
    review_state: str
    current: bool
    suppressed: bool
    deleted: bool
    first_observed_at: datetime
    last_observed_at: datetime

    @classmethod
    def from_domain(cls, item: ReportingLineView) -> ReportingLineResponse:
        return cls(**asdict(item))


class ProfessionalContactResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_key: str
    channel_type: str
    value: str | None
    organization_id: UUID | None
    confidence: float = Field(ge=0, le=1)
    review_state: str
    current: bool
    suppressed: bool
    deleted: bool
    last_observed_at: datetime
    retention_until: datetime

    @classmethod
    def from_domain(cls, item: ProfessionalContactView) -> ProfessionalContactResponse:
        return cls(**asdict(item))


class CommunityContextResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context_key: str
    community_name: str
    context_type: str
    context_value: str | None
    acquisition_mode: str
    organization_id: UUID | None
    confidence: float = Field(ge=0, le=1)
    review_state: str
    current: bool
    suppressed: bool
    deleted: bool
    last_observed_at: datetime

    @classmethod
    def from_domain(cls, item: CommunityContextView) -> CommunityContextResponse:
        return cls(**asdict(item))


class ServiceRelevanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mapping_key: str
    service_family: str
    rationale: str
    confidence: float = Field(ge=0, le=1)
    review_state: str
    source_claim_keys: list[str]

    @classmethod
    def from_domain(cls, item: ServiceRelevanceView) -> ServiceRelevanceResponse:
        values = asdict(item)
        values["source_claim_keys"] = list(item.source_claim_keys)
        return cls(**values)


class ProfessionalEvidenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_type: str
    source_id: str
    source_record_key: str | None
    source_url: str | None
    observed_at: datetime
    claim_type: str | None
    review_state: str
    suppressed: bool
    deleted: bool
    retention_until: datetime

    @classmethod
    def from_domain(cls, item: ProfessionalEvidenceView) -> ProfessionalEvidenceResponse:
        return cls(**asdict(item))


class ProfessionalPersonPageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ProfessionalPersonResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)

    @classmethod
    def from_domain(cls, page: ProfessionalPersonPage) -> ProfessionalPersonPageResponse:
        return cls(
            items=[ProfessionalPersonResponse.from_domain(item) for item in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )


class ProfessionalPersonDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person: ProfessionalPersonResponse
    roles: list[ProfessionalRoleResponse]
    reporting_as_subject: list[ReportingLineResponse]
    reporting_as_manager: list[ReportingLineResponse]
    contacts: list[ProfessionalContactResponse]
    community_context: list[CommunityContextResponse]
    service_relevance: list[ServiceRelevanceResponse]
    evidence_history: list[ProfessionalEvidenceResponse]
    evidence_disclaimer: str

    @classmethod
    def from_domain(cls, detail: ProfessionalPersonDetail) -> ProfessionalPersonDetailResponse:
        return cls(
            person=ProfessionalPersonResponse.from_domain(detail.person),
            roles=[ProfessionalRoleResponse.from_domain(item) for item in detail.roles],
            reporting_as_subject=[
                ReportingLineResponse.from_domain(item) for item in detail.reporting_as_subject
            ],
            reporting_as_manager=[
                ReportingLineResponse.from_domain(item) for item in detail.reporting_as_manager
            ],
            contacts=[ProfessionalContactResponse.from_domain(item) for item in detail.contacts],
            community_context=[
                CommunityContextResponse.from_domain(item) for item in detail.community_context
            ],
            service_relevance=[
                ServiceRelevanceResponse.from_domain(item) for item in detail.service_relevance
            ],
            evidence_history=[
                ProfessionalEvidenceResponse.from_domain(item) for item in detail.evidence_history
            ],
            evidence_disclaimer=(
                "Professional context is source-aware and temporal. A role claim is not "
                "verified employment, a public profile is not automation authorization, "
                "and contact relevance is not outreach authorization."
            ),
        )


class OrganizationProfessionalMapResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: UUID
    people: list[ProfessionalPersonResponse]
    reporting_lines: list[ReportingLineResponse]
    organization_contacts: list[ProfessionalContactResponse]
    community_context: list[CommunityContextResponse]
    privacy_disclaimer: str

    @classmethod
    def from_domain(cls, item: OrganizationProfessionalMap) -> OrganizationProfessionalMapResponse:
        return cls(
            organization_id=item.organization_id,
            people=[ProfessionalPersonResponse.from_domain(value) for value in item.people],
            reporting_lines=[ReportingLineResponse.from_domain(value) for value in item.reporting_lines],
            organization_contacts=[
                ProfessionalContactResponse.from_domain(value)
                for value in item.organization_contacts
            ],
            community_context=[
                CommunityContextResponse.from_domain(value) for value in item.community_context
            ],
            privacy_disclaimer=(
                "The map contains bounded professional evidence only. Same names are not "
                "merged automatically and hierarchy is not inferred transitively."
            ),
        )

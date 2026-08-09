from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProfessionalPersonFilters:
    organization_id: UUID | None = None
    employment_state: str | None = None
    review_state: str | None = None
    lawful_basis: str | None = None
    include_suppressed: bool = False
    include_deleted: bool = False
    query: str | None = None


@dataclass(frozen=True, slots=True)
class ProfessionalPersonSummary:
    person_key: str
    display_name: str | None
    confidence: float
    review_state: str
    lawful_basis: str
    processing_purpose: str
    current: bool
    suppressed: bool
    deleted: bool
    last_observed_at: datetime
    retention_until: datetime
    current_role: str | None = None
    current_team: str | None = None
    organization_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ProfessionalRoleView:
    claim_key: str
    role_title: str | None
    team_name: str | None
    organization_id: UUID | None
    claimed_organization_name: str | None
    employment_state: str
    confidence: float
    review_state: str
    first_observed_at: datetime
    last_observed_at: datetime
    retention_until: datetime
    suppressed: bool
    deleted: bool


@dataclass(frozen=True, slots=True)
class ReportingLineView:
    claim_key: str
    subject_person_key: str
    manager_person_key: str
    organization_id: UUID | None
    confidence: float
    review_state: str
    current: bool
    suppressed: bool
    deleted: bool
    first_observed_at: datetime
    last_observed_at: datetime


@dataclass(frozen=True, slots=True)
class ProfessionalContactView:
    contact_key: str
    channel_type: str
    value: str | None
    organization_id: UUID | None
    confidence: float
    review_state: str
    current: bool
    suppressed: bool
    deleted: bool
    last_observed_at: datetime
    retention_until: datetime


@dataclass(frozen=True, slots=True)
class CommunityContextView:
    context_key: str
    community_name: str
    context_type: str
    context_value: str | None
    acquisition_mode: str
    organization_id: UUID | None
    confidence: float
    review_state: str
    current: bool
    suppressed: bool
    deleted: bool
    last_observed_at: datetime


@dataclass(frozen=True, slots=True)
class ServiceRelevanceView:
    mapping_key: str
    service_family: str
    rationale: str
    confidence: float
    review_state: str
    source_claim_keys: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProfessionalEvidenceView:
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


@dataclass(frozen=True, slots=True)
class ProfessionalPersonDetail:
    person: ProfessionalPersonSummary
    roles: tuple[ProfessionalRoleView, ...]
    reporting_as_subject: tuple[ReportingLineView, ...]
    reporting_as_manager: tuple[ReportingLineView, ...]
    contacts: tuple[ProfessionalContactView, ...]
    community_context: tuple[CommunityContextView, ...]
    service_relevance: tuple[ServiceRelevanceView, ...]
    evidence_history: tuple[ProfessionalEvidenceView, ...]


@dataclass(frozen=True, slots=True)
class ProfessionalPersonPage:
    items: tuple[ProfessionalPersonSummary, ...]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class OrganizationProfessionalMap:
    organization_id: UUID
    people: tuple[ProfessionalPersonSummary, ...]
    reporting_lines: tuple[ReportingLineView, ...]
    organization_contacts: tuple[ProfessionalContactView, ...]
    community_context: tuple[CommunityContextView, ...]

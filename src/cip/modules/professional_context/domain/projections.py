from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from cip.modules.professional_context.domain.enums import (
    CommunityAcquisitionMode,
    ContactChannelType,
    EmploymentState,
    LawfulBasis,
    ProfessionalReviewState,
)


@dataclass(frozen=True, slots=True)
class ProfessionalPersonProjection:
    person_key: str
    display_name: str
    source_id: str
    confidence: float
    review_state: ProfessionalReviewState
    lawful_basis: LawfulBasis
    lawful_basis_reference: str
    purpose: str
    current: bool
    suppressed: bool
    deleted: bool
    last_observed_at: datetime
    retention_until: datetime


@dataclass(frozen=True, slots=True)
class ProfessionalRoleProjection:
    claim_key: str
    person_key: str
    organization_id: UUID | None
    claimed_organization_name: str | None
    role_title: str
    team_name: str | None
    employment_state: EmploymentState
    confidence: float
    review_state: ProfessionalReviewState
    lawful_basis: LawfulBasis
    lawful_basis_reference: str
    purpose: str
    suppressed: bool
    deleted: bool
    evidence_count: int
    first_observed_at: datetime
    last_observed_at: datetime
    retention_until: datetime


@dataclass(frozen=True, slots=True)
class ReportingLineProjection:
    claim_key: str
    subject_person_key: str
    manager_person_key: str
    organization_id: UUID | None
    confidence: float
    review_state: ProfessionalReviewState
    lawful_basis: LawfulBasis
    lawful_basis_reference: str
    purpose: str
    current: bool
    suppressed: bool
    deleted: bool
    first_observed_at: datetime
    last_observed_at: datetime
    retention_until: datetime


@dataclass(frozen=True, slots=True)
class ProfessionalContactProjection:
    contact_key: str
    channel_type: ContactChannelType
    value: str
    organization_id: UUID | None
    person_key: str | None
    confidence: float
    review_state: ProfessionalReviewState
    lawful_basis: LawfulBasis
    lawful_basis_reference: str
    purpose: str
    current: bool
    suppressed: bool
    deleted: bool
    last_observed_at: datetime
    retention_until: datetime


@dataclass(frozen=True, slots=True)
class PublicCommunityProjection:
    context_key: str
    community_name: str
    context_type: str
    context_value: str
    acquisition_mode: CommunityAcquisitionMode
    organization_id: UUID | None
    person_key: str | None
    confidence: float
    review_state: ProfessionalReviewState
    lawful_basis: LawfulBasis
    lawful_basis_reference: str
    purpose: str
    current: bool
    suppressed: bool
    deleted: bool
    last_observed_at: datetime
    retention_until: datetime

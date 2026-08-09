from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from cip.modules.professional_context.domain.enums import (
    EmploymentState,
    OrganizationLinkStatus,
    ProfessionalClaimType,
    ProfessionalReviewState,
)
from cip.modules.professional_context.domain.privacy import ProfessionalProcessingContext
from cip.modules.professional_context.domain.validation import (
    aware_time,
    confidence,
    optional_text,
    optional_time,
    optional_url,
    require_text,
    validity,
)


@dataclass(frozen=True, slots=True)
class ProfessionalRoleClaim:
    claim_key: str
    person_key: str
    source_id: str
    source_record_key: str
    role_title: str
    observed_at: datetime
    confidence: float
    processing: ProfessionalProcessingContext
    organization_id: UUID | None = None
    claimed_organization_name: str | None = None
    organization_link_status: OrganizationLinkStatus = OrganizationLinkStatus.UNRESOLVED
    team_name: str | None = None
    claim_type: ProfessionalClaimType = ProfessionalClaimType.ASSERTION
    review_state: ProfessionalReviewState = ProfessionalReviewState.UNREVIEWED
    source_url: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    expires_at: datetime | None = None
    active: bool = True
    historical_only: bool = False
    suppressed: bool = False
    deleted: bool = False
    supersedes_record_key: str | None = None

    def __post_init__(self) -> None:
        _normalize_role(self)
        if self.organization_link_status is OrganizationLinkStatus.EXACT:
            if self.organization_id is None:
                raise ValueError("exact organization link requires organization_id")
        elif self.organization_id is not None:
            raise ValueError("non-exact organization link cannot carry organization_id")

    def employment_state_at(
        self,
        now: datetime,
        *,
        stale_after: timedelta = timedelta(days=365),
    ) -> EmploymentState:
        current = aware_time(now, "now")
        if self.claim_type is ProfessionalClaimType.RETRACTION:
            return EmploymentState.RETRACTED
        if self.claim_type is ProfessionalClaimType.DISPUTE:
            return EmploymentState.DISPUTED
        if self.deleted or self.suppressed or not self.active:
            return EmploymentState.HISTORICAL
        if self.valid_until is not None and self.valid_until <= current:
            return EmploymentState.HISTORICAL
        if self.historical_only:
            return EmploymentState.HISTORICAL
        freshness_anchor = max(
            value for value in (self.observed_at, self.valid_from) if value is not None
        )
        if current - freshness_anchor > stale_after:
            return EmploymentState.STALE
        if self.valid_from is not None and self.valid_from > current:
            return EmploymentState.UNKNOWN
        return EmploymentState.CURRENT


@dataclass(frozen=True, slots=True)
class ReportingLineClaim:
    claim_key: str
    subject_person_key: str
    manager_person_key: str
    source_id: str
    source_record_key: str
    observed_at: datetime
    confidence: float
    processing: ProfessionalProcessingContext
    organization_id: UUID | None = None
    claim_type: ProfessionalClaimType = ProfessionalClaimType.ASSERTION
    review_state: ProfessionalReviewState = ProfessionalReviewState.REVIEW_REQUIRED
    source_url: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    active: bool = True
    suppressed: bool = False
    deleted: bool = False
    supersedes_record_key: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("claim_key", "subject_person_key", "manager_person_key"):
            object.__setattr__(
                self,
                field_name,
                require_text(getattr(self, field_name), field_name, 500),
            )
        if self.subject_person_key == self.manager_person_key:
            raise ValueError("reporting-line claim cannot be self-referential")
        object.__setattr__(self, "source_id", require_text(self.source_id, "source_id", 200))
        object.__setattr__(
            self,
            "source_record_key",
            require_text(self.source_record_key, "source_record_key", 500),
        )
        object.__setattr__(self, "observed_at", aware_time(self.observed_at, "observed_at"))
        object.__setattr__(self, "confidence", confidence(self.confidence))
        object.__setattr__(self, "source_url", optional_url(self.source_url, "source_url"))
        object.__setattr__(self, "valid_from", optional_time(self.valid_from, "valid_from"))
        object.__setattr__(self, "valid_until", optional_time(self.valid_until, "valid_until"))
        object.__setattr__(
            self,
            "supersedes_record_key",
            optional_text(self.supersedes_record_key, "supersedes_record_key", 500),
        )
        validity(self.valid_from, self.valid_until)

    @property
    def current_evidence(self) -> bool:
        return (
            self.active
            and not self.suppressed
            and not self.deleted
            and self.claim_type
            not in {ProfessionalClaimType.DISPUTE, ProfessionalClaimType.RETRACTION}
        )

    @property
    def permits_transitive_inference(self) -> bool:
        return False


def _normalize_role(claim: ProfessionalRoleClaim) -> None:
    for field_name, maximum in (
        ("claim_key", 500),
        ("person_key", 200),
        ("source_id", 200),
        ("source_record_key", 500),
        ("role_title", 300),
    ):
        object.__setattr__(
            claim,
            field_name,
            require_text(getattr(claim, field_name), field_name, maximum),
        )
    object.__setattr__(
        claim,
        "claimed_organization_name",
        optional_text(claim.claimed_organization_name, "claimed_organization_name", 500),
    )
    object.__setattr__(claim, "team_name", optional_text(claim.team_name, "team_name", 300))
    object.__setattr__(claim, "source_url", optional_url(claim.source_url, "source_url"))
    object.__setattr__(claim, "observed_at", aware_time(claim.observed_at, "observed_at"))
    object.__setattr__(claim, "confidence", confidence(claim.confidence))
    for field_name in ("valid_from", "valid_until", "expires_at"):
        object.__setattr__(claim, field_name, optional_time(getattr(claim, field_name), field_name))
    object.__setattr__(
        claim,
        "supersedes_record_key",
        optional_text(claim.supersedes_record_key, "supersedes_record_key", 500),
    )
    validity(claim.valid_from, claim.valid_until)

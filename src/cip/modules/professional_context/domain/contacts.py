from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from cip.modules.data_governance.domain.suppression import SuppressionChannel
from cip.modules.professional_context.domain.enums import (
    ContactChannelType,
    ContactEvidenceScope,
    ProfessionalClaimType,
    ProfessionalReviewState,
)
from cip.modules.professional_context.domain.privacy import ProfessionalProcessingContext
from cip.modules.professional_context.domain.validation import (
    aware_time,
    confidence,
    optional_text,
    optional_url,
    require_text,
)


@dataclass(frozen=True, slots=True)
class ProfessionalContactEvidence:
    contact_key: str
    channel_type: ContactChannelType
    evidence_scope: ContactEvidenceScope
    value: str
    source_id: str
    source_record_key: str
    observed_at: datetime
    confidence: float
    processing: ProfessionalProcessingContext
    organization_id: UUID | None = None
    person_key: str | None = None
    source_url: str | None = None
    claim_type: ProfessionalClaimType = ProfessionalClaimType.ASSERTION
    review_state: ProfessionalReviewState = ProfessionalReviewState.REVIEW_REQUIRED
    active: bool = True
    suppressed: bool = False
    deleted: bool = False
    supersedes_record_key: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "contact_key",
            require_text(self.contact_key, "contact_key", 500),
        )
        object.__setattr__(self, "value", require_text(self.value, "value", 2_048))
        object.__setattr__(self, "source_id", require_text(self.source_id, "source_id", 200))
        object.__setattr__(
            self,
            "source_record_key",
            require_text(self.source_record_key, "source_record_key", 500),
        )
        object.__setattr__(
            self,
            "person_key",
            optional_text(self.person_key, "person_key", 200),
        )
        object.__setattr__(self, "source_url", optional_url(self.source_url, "source_url"))
        object.__setattr__(self, "observed_at", aware_time(self.observed_at, "observed_at"))
        object.__setattr__(self, "confidence", confidence(self.confidence))
        object.__setattr__(
            self,
            "supersedes_record_key",
            optional_text(self.supersedes_record_key, "supersedes_record_key", 500),
        )
        if self.organization_id is None and self.person_key is None:
            raise ValueError("business contact evidence requires organization or person context")
        _validate_channel(self)

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
    def suppression_channel(self) -> SuppressionChannel:
        if self.channel_type is ContactChannelType.BUSINESS_EMAIL:
            return SuppressionChannel.EMAIL
        if self.channel_type is ContactChannelType.PROFESSIONAL_PROFILE:
            return SuppressionChannel.PROFESSIONAL_PROFILE
        return SuppressionChannel.ORGANIZATION

    @property
    def authorizes_outreach(self) -> bool:
        return False

    @property
    def authorizes_source_automation(self) -> bool:
        return False


def _validate_channel(evidence: ProfessionalContactEvidence) -> None:
    if evidence.channel_type is ContactChannelType.BUSINESS_EMAIL:
        local, separator, domain = evidence.value.partition("@")
        if not separator or not local or "." not in domain:
            raise ValueError("business email must contain a valid-looking domain")
        return
    if evidence.channel_type is ContactChannelType.BUSINESS_EMAIL_PATTERN:
        if "@" not in evidence.value:
            raise ValueError("business email pattern must include a domain")
        if evidence.organization_id is None:
            raise ValueError("business email pattern requires organization context")
        return
    if evidence.channel_type is ContactChannelType.SWITCHBOARD:
        if evidence.organization_id is None or evidence.person_key is not None:
            raise ValueError("switchboard must be organization-level contact context")
        if not any(character.isdigit() for character in evidence.value):
            raise ValueError("switchboard must contain digits")
        return
    if evidence.channel_type is ContactChannelType.CONTACT_FORM:
        if evidence.organization_id is None:
            raise ValueError("contact form requires organization context")
        optional_url(evidence.value, "contact form URL")
        return
    if evidence.person_key is None:
        raise ValueError("professional profile requires person context")
    optional_url(evidence.value, "professional profile URL")

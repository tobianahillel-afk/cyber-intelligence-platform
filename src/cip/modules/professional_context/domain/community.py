from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from cip.modules.professional_context.domain.enums import (
    CommunityAcquisitionMode,
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
class PublicCommunityContext:
    context_key: str
    community_name: str
    context_type: str
    context_value: str
    acquisition_mode: CommunityAcquisitionMode
    authorization_reference: str
    source_id: str
    source_record_key: str
    observed_at: datetime
    confidence: float
    processing: ProfessionalProcessingContext
    person_key: str | None = None
    organization_id: UUID | None = None
    source_url: str | None = None
    review_state: ProfessionalReviewState = ProfessionalReviewState.REVIEW_REQUIRED
    active: bool = True
    suppressed: bool = False
    deleted: bool = False
    metadata_only: bool = True

    def __post_init__(self) -> None:
        for field_name, maximum in (
            ("context_key", 500),
            ("community_name", 300),
            ("context_type", 100),
            ("context_value", 500),
            ("authorization_reference", 500),
            ("source_id", 200),
            ("source_record_key", 500),
        ):
            object.__setattr__(
                self,
                field_name,
                require_text(getattr(self, field_name), field_name, maximum),
            )
        object.__setattr__(
            self,
            "person_key",
            optional_text(self.person_key, "person_key", 200),
        )
        object.__setattr__(self, "source_url", optional_url(self.source_url, "source_url"))
        object.__setattr__(self, "observed_at", aware_time(self.observed_at, "observed_at"))
        object.__setattr__(self, "confidence", confidence(self.confidence))
        if self.person_key is None and self.organization_id is None:
            raise ValueError("community context requires professional person or organization context")
        if not self.metadata_only:
            raise ValueError("community context accepts metadata only")

    @property
    def authorizes_source_automation(self) -> bool:
        return False

    @property
    def authorizes_outreach(self) -> bool:
        return False

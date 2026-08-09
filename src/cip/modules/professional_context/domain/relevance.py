from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from cip.modules.professional_context.domain.enums import ProfessionalReviewState
from cip.modules.professional_context.domain.validation import aware_time, confidence, require_text
from cip.modules.service_taxonomy.domain.models import CyberServiceFamily


@dataclass(frozen=True, slots=True)
class ProfessionalServiceRelevance:
    mapping_key: str
    service_family: CyberServiceFamily
    rationale: str
    confidence: float
    source_claim_keys: tuple[str, ...]
    created_at: datetime
    person_key: str | None = None
    organization_id: UUID | None = None
    review_state: ProfessionalReviewState = ProfessionalReviewState.REVIEW_REQUIRED

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "mapping_key",
            require_text(self.mapping_key, "mapping_key", 500),
        )
        object.__setattr__(self, "rationale", require_text(self.rationale, "rationale", 500))
        object.__setattr__(self, "confidence", confidence(self.confidence))
        object.__setattr__(self, "created_at", aware_time(self.created_at, "created_at"))
        claim_keys = tuple(
            dict.fromkeys(require_text(value, "source_claim_key", 500) for value in self.source_claim_keys)
        )
        if not claim_keys:
            raise ValueError("service relevance requires source claim keys")
        object.__setattr__(self, "source_claim_keys", claim_keys)
        if self.person_key is None and self.organization_id is None:
            raise ValueError("service relevance requires person or organization context")
        if self.person_key is not None:
            object.__setattr__(
                self,
                "person_key",
                require_text(self.person_key, "person_key", 200),
            )

    @property
    def creates_commercial_signal(self) -> bool:
        return False

    @property
    def creates_opportunity(self) -> bool:
        return False

    @property
    def authorizes_outreach(self) -> bool:
        return False

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

from cip.modules.professional_context.domain.enums import ProfessionalReviewState
from cip.modules.professional_context.domain.privacy import ProfessionalProcessingContext
from cip.modules.professional_context.domain.validation import (
    aware_time,
    confidence,
    optional_url,
    require_text,
)


def source_person_key(source_id: str, source_record_key: str) -> str:
    source = require_text(source_id, "source_id", 200)
    record = require_text(source_record_key, "source_record_key", 500)
    digest = sha256(f"{source}\x1f{record}".encode()).hexdigest()
    return f"professional-person:{digest}"


@dataclass(frozen=True, slots=True)
class ProfessionalPersonReference:
    person_key: str
    display_name: str
    source_id: str
    source_kind: str
    source_record_key: str
    observed_at: datetime
    confidence: float
    processing: ProfessionalProcessingContext
    review_state: ProfessionalReviewState = ProfessionalReviewState.UNREVIEWED
    source_url: str | None = None
    active: bool = True
    suppressed: bool = False
    deleted: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "person_key", require_text(self.person_key, "person_key", 200))
        object.__setattr__(
            self,
            "display_name",
            require_text(self.display_name, "display_name", 300),
        )
        object.__setattr__(self, "source_id", require_text(self.source_id, "source_id", 200))
        object.__setattr__(
            self,
            "source_kind",
            require_text(self.source_kind, "source_kind", 80),
        )
        object.__setattr__(
            self,
            "source_record_key",
            require_text(self.source_record_key, "source_record_key", 500),
        )
        object.__setattr__(self, "observed_at", aware_time(self.observed_at, "observed_at"))
        object.__setattr__(self, "confidence", confidence(self.confidence))
        object.__setattr__(self, "source_url", optional_url(self.source_url, "source_url"))
        expected_key = source_person_key(self.source_id, self.source_record_key)
        if self.person_key != expected_key:
            raise ValueError("source person_key must be derived from source id and record key")

    @property
    def visible(self) -> bool:
        return self.active and not self.suppressed and not self.deleted

    @property
    def authorizes_outreach(self) -> bool:
        return False

    @property
    def authorizes_source_automation(self) -> bool:
        return False

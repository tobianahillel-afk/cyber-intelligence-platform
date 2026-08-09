from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from cip.modules.professional_context.domain.enums import LawfulBasis
from cip.modules.professional_context.domain.validation import aware_time, require_text


@dataclass(frozen=True, slots=True)
class ProfessionalProcessingContext:
    lawful_basis: LawfulBasis
    lawful_basis_reference: str
    purpose: str
    reviewed_at: datetime
    retention_until: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "lawful_basis_reference",
            require_text(self.lawful_basis_reference, "lawful_basis_reference", 500),
        )
        object.__setattr__(self, "purpose", require_text(self.purpose, "purpose", 300))
        reviewed_at = aware_time(self.reviewed_at, "reviewed_at")
        retention_until = aware_time(self.retention_until, "retention_until")
        if retention_until <= reviewed_at:
            raise ValueError("retention_until must be later than reviewed_at")
        object.__setattr__(self, "reviewed_at", reviewed_at)
        object.__setattr__(self, "retention_until", retention_until)

    def permits_processing_at(self, when: datetime) -> bool:
        current = aware_time(when, "when")
        return current < self.retention_until

    @property
    def requires_lawful_basis_review(self) -> bool:
        return self.lawful_basis is LawfulBasis.REVIEW_REQUIRED

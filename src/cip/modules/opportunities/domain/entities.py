from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from cip.modules.opportunities.domain.scoring import OpportunityScore
from cip.modules.opportunities.domain.signal_entities import (
    CommercialSignal,
    HypothesisStatus,
    NeedHorizon,
    NeedHypothesis,
    NeedHypothesisClass,
    NeedUrgency,
    OpportunityFamily,
    SignalPolarity,
    SignalType,
    SourceContribution,
)
from cip.shared.kernel.time import require_aware_utc, utc_now


class OpportunityState(StrEnum):
    NEEDS_REVIEW = "needs_review"
    QUALIFIED = "qualified"
    REJECTED = "rejected"
    SNOOZED = "snoozed"
    ENRICHMENT_REQUESTED = "enrichment_requested"


class ReviewAction(StrEnum):
    QUALIFY = "qualify"
    REJECT = "reject"
    SNOOZE = "snooze"
    REQUEST_ENRICHMENT = "request_enrichment"
    REOPEN = "reopen"


class DataQuality(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"


@dataclass(frozen=True, slots=True)
class Opportunity:
    organization_id: UUID
    hypothesis_id: UUID
    recommended_offer: str
    relevant_roles: tuple[str, ...]
    trigger_summary: str
    next_action: str
    score: OpportunityScore
    confidence: float
    last_evidence_at: datetime
    data_quality: DataQuality
    id: UUID = field(default_factory=uuid4)
    state: OpportunityState = OpportunityState.NEEDS_REVIEW
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    snoozed_until: datetime | None = None
    review_note: str | None = None
    rejected_reason: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("recommended_offer", "trigger_summary", "next_action"):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} is required")
            object.__setattr__(self, field_name, value)
        roles = tuple(
            dict.fromkeys(role.strip() for role in self.relevant_roles if role.strip())
        )
        if not roles:
            raise ValueError("relevant_roles are required")
        if self.score.organization_id != self.organization_id:
            raise ValueError("score organization must match opportunity organization")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(self, "relevant_roles", roles)
        for field_name in ("last_evidence_at", "created_at", "updated_at"):
            object.__setattr__(
                self,
                field_name,
                require_aware_utc(getattr(self, field_name), field_name=field_name),
            )
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot precede created_at")
        if self.snoozed_until is not None:
            object.__setattr__(
                self,
                "snoozed_until",
                require_aware_utc(self.snoozed_until, field_name="snoozed_until"),
            )

    def review(
        self,
        action: ReviewAction,
        *,
        now: datetime,
        note: str | None = None,
        snoozed_until: datetime | None = None,
    ) -> Opportunity:
        reviewed_at = require_aware_utc(now, field_name="now")
        normalized_note = note.strip() if note is not None and note.strip() else None
        if action is ReviewAction.QUALIFY:
            return replace(
                self,
                state=OpportunityState.QUALIFIED,
                updated_at=reviewed_at,
                review_note=normalized_note,
                rejected_reason=None,
                snoozed_until=None,
            )
        if action is ReviewAction.REJECT:
            if normalized_note is None:
                raise ValueError("reject requires a reason")
            return replace(
                self,
                state=OpportunityState.REJECTED,
                updated_at=reviewed_at,
                review_note=normalized_note,
                rejected_reason=normalized_note,
                snoozed_until=None,
            )
        if action is ReviewAction.SNOOZE:
            if snoozed_until is None:
                raise ValueError("snooze requires snoozed_until")
            until = require_aware_utc(snoozed_until, field_name="snoozed_until")
            if until <= reviewed_at:
                raise ValueError("snoozed_until must be later than now")
            return replace(
                self,
                state=OpportunityState.SNOOZED,
                updated_at=reviewed_at,
                review_note=normalized_note,
                rejected_reason=None,
                snoozed_until=until,
            )
        if action is ReviewAction.REQUEST_ENRICHMENT:
            return replace(
                self,
                state=OpportunityState.ENRICHMENT_REQUESTED,
                updated_at=reviewed_at,
                review_note=normalized_note,
                rejected_reason=None,
                snoozed_until=None,
            )
        if action is ReviewAction.REOPEN:
            return replace(
                self,
                state=OpportunityState.NEEDS_REVIEW,
                updated_at=reviewed_at,
                review_note=normalized_note,
                rejected_reason=None,
                snoozed_until=None,
            )
        raise ValueError(f"unsupported review action: {action.value}")


__all__ = [
    "CommercialSignal",
    "DataQuality",
    "HypothesisStatus",
    "NeedHorizon",
    "NeedHypothesis",
    "NeedHypothesisClass",
    "NeedUrgency",
    "Opportunity",
    "OpportunityFamily",
    "OpportunityState",
    "ReviewAction",
    "SignalPolarity",
    "SignalType",
    "SourceContribution",
]

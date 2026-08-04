from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from uuid import UUID, uuid4

from cip.modules.opportunities.domain.scoring import OpportunityScore
from cip.shared.kernel.time import require_aware_utc, utc_now


class SignalType(StrEnum):
    PUBLIC_TENDER = "public_tender"
    JOB_POSTING = "job_posting"


class OpportunityFamily(StrEnum):
    SIEM_SOC_BUYING_INTENT = "siem_soc_buying_intent"


class HypothesisStatus(StrEnum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    DISMISSED = "dismissed"


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
class CommercialSignal:
    organization_id: UUID
    evidence_id: UUID
    signal_type: SignalType
    title: str
    summary: str
    confidence: float
    collected_at: datetime
    id: UUID = field(default_factory=uuid4)
    matched_terms: tuple[str, ...] = ()
    published_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        title = self.title.strip()
        summary = self.summary.strip()
        if not title:
            raise ValueError("title is required")
        if len(title) > 500:
            raise ValueError("title cannot exceed 500 characters")
        if not summary:
            raise ValueError("summary is required")
        if len(summary) > 4_000:
            raise ValueError("summary cannot exceed 4000 characters")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "summary", summary)
        object.__setattr__(self, "matched_terms", _normalized_terms(self.matched_terms))
        for field_name in ("collected_at", "created_at"):
            object.__setattr__(
                self,
                field_name,
                require_aware_utc(getattr(self, field_name), field_name=field_name),
            )
        for field_name in ("published_at", "expires_at"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    require_aware_utc(value, field_name=field_name),
                )
        if self.expires_at is not None and self.expires_at <= self.collected_at:
            raise ValueError("expires_at must be later than collected_at")

    @property
    def idempotency_key(self) -> str:
        material = f"{self.organization_id}\0{self.evidence_id}\0{self.signal_type.value}"
        return sha256(material.encode("utf-8")).hexdigest()

    @property
    def effective_at(self) -> datetime:
        return self.published_at or self.collected_at


@dataclass(frozen=True, slots=True)
class NeedHypothesis:
    organization_id: UUID
    family: OpportunityFamily
    rule_id: str
    rule_version: str
    rationale: str
    signal_ids: tuple[UUID, ...]
    evidence_ids: tuple[UUID, ...]
    generated_at: datetime
    expires_at: datetime
    id: UUID = field(default_factory=uuid4)
    status: HypothesisStatus = HypothesisStatus.PROPOSED

    def __post_init__(self) -> None:
        if not self.rule_id.strip() or not self.rule_version.strip():
            raise ValueError("rule_id and rule_version are required")
        if not self.rationale.strip():
            raise ValueError("rationale is required")
        if not self.signal_ids or not self.evidence_ids:
            raise ValueError("a hypothesis requires signals and evidence")
        generated_at = require_aware_utc(self.generated_at, field_name="generated_at")
        expires_at = require_aware_utc(self.expires_at, field_name="expires_at")
        if expires_at <= generated_at:
            raise ValueError("expires_at must be later than generated_at")
        object.__setattr__(self, "generated_at", generated_at)
        object.__setattr__(self, "expires_at", expires_at)
        object.__setattr__(self, "signal_ids", tuple(dict.fromkeys(self.signal_ids)))
        object.__setattr__(self, "evidence_ids", tuple(dict.fromkeys(self.evidence_ids)))

    @property
    def idempotency_key(self) -> str:
        material = (
            f"{self.organization_id}\0{self.family.value}\0"
            f"{self.rule_id}\0{self.rule_version}"
        )
        return sha256(material.encode("utf-8")).hexdigest()


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
        roles = tuple(dict.fromkeys(role.strip() for role in self.relevant_roles if role.strip()))
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


def _normalized_terms(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value.strip().lower() for value in values if value.strip()))

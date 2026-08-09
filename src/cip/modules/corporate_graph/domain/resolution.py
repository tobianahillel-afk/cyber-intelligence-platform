from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from cip.shared.kernel.time import require_aware_utc, utc_now


class ResolutionMethod(StrEnum):
    EXACT_IDENTIFIER = "exact_identifier"
    EXACT_SOURCE_BINDING = "exact_source_binding"
    REVIEWED_ALIAS = "reviewed_alias"
    EXACT_NAME_AND_POSTCODE = "exact_name_and_postcode"
    DOMAIN_OWNERSHIP = "domain_ownership"
    PROBABILISTIC_NAME_ADDRESS = "probabilistic_name_address"
    PROBABILISTIC_CONTEXT = "probabilistic_context"


class ResolutionCandidateState(StrEnum):
    PENDING = "pending"
    AUTO_CONFIRMED = "auto_confirmed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ResolutionDecisionType(StrEnum):
    MERGE = "merge"
    REJECT = "reject"
    SPLIT = "split"
    OVERRIDE = "override"
    RESTORE = "restore"


_AUTO_CONFIRM_METHODS = {
    ResolutionMethod.EXACT_IDENTIFIER,
    ResolutionMethod.EXACT_SOURCE_BINDING,
}


@dataclass(frozen=True, slots=True)
class EntityResolutionCandidate:
    node_key: str
    candidate_organization_id: UUID
    method: ResolutionMethod
    score: float
    reasons: tuple[str, ...]
    created_at: datetime
    state: ResolutionCandidateState = ResolutionCandidateState.PENDING
    candidate_id: UUID = field(default_factory=uuid4)
    conflicting_organization_ids: tuple[UUID, ...] = ()
    requires_review: bool = True

    def __post_init__(self) -> None:
        if not self.node_key.strip() or len(self.node_key) > 500:
            raise ValueError("node_key must be between 1 and 500 characters")
        if not 0 <= self.score <= 1:
            raise ValueError("score must be between 0 and 1")
        reasons = _normalize_reasons(self.reasons)
        if not reasons:
            raise ValueError("resolution candidate requires at least one reason")
        object.__setattr__(self, "reasons", reasons)
        object.__setattr__(
            self,
            "created_at",
            require_aware_utc(self.created_at, field_name="created_at"),
        )
        conflicts = tuple(dict.fromkeys(self.conflicting_organization_ids))
        if self.candidate_organization_id in conflicts:
            raise ValueError("candidate organization cannot also be a conflict")
        object.__setattr__(self, "conflicting_organization_ids", conflicts)
        if self.state is ResolutionCandidateState.AUTO_CONFIRMED:
            if not can_auto_confirm(self.method, conflicts=conflicts):
                raise ValueError("candidate is not eligible for automatic confirmation")
            object.__setattr__(self, "requires_review", False)
        if self.method not in _AUTO_CONFIRM_METHODS:
            object.__setattr__(self, "requires_review", True)


@dataclass(frozen=True, slots=True)
class ResolutionDecision:
    candidate_id: UUID
    node_key: str
    decision_type: ResolutionDecisionType
    actor: str
    reason: str
    decided_at: datetime
    decision_id: UUID = field(default_factory=uuid4)
    organization_id: UUID | None = None
    reverses_decision_id: UUID | None = None
    blast_radius_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if not self.node_key.strip() or len(self.node_key) > 500:
            raise ValueError("node_key must be between 1 and 500 characters")
        _required_text(self.actor, "actor", 200)
        _required_text(self.reason, "reason", 1_000)
        object.__setattr__(
            self,
            "decided_at",
            require_aware_utc(self.decided_at, field_name="decided_at"),
        )
        if self.decision_type in {
            ResolutionDecisionType.MERGE,
            ResolutionDecisionType.OVERRIDE,
            ResolutionDecisionType.RESTORE,
        } and self.organization_id is None:
            raise ValueError("merge, override, and restore decisions require organization_id")
        if self.decision_type in {
            ResolutionDecisionType.RESTORE,
            ResolutionDecisionType.SPLIT,
        } and self.reverses_decision_id is None:
            raise ValueError("restore and split decisions must reference a prior decision")
        if self.blast_radius_fingerprint is None:
            raise ValueError("resolution decisions require a blast-radius preview fingerprint")
        _required_text(
            self.blast_radius_fingerprint,
            "blast_radius_fingerprint",
            64,
        )

    @classmethod
    def create(
        cls,
        *,
        candidate_id: UUID,
        node_key: str,
        decision_type: ResolutionDecisionType,
        actor: str,
        reason: str,
        organization_id: UUID | None,
        blast_radius_fingerprint: str,
        reverses_decision_id: UUID | None = None,
    ) -> ResolutionDecision:
        return cls(
            candidate_id=candidate_id,
            node_key=node_key,
            decision_type=decision_type,
            actor=actor,
            reason=reason,
            organization_id=organization_id,
            reverses_decision_id=reverses_decision_id,
            blast_radius_fingerprint=blast_radius_fingerprint,
            decided_at=utc_now(),
        )


def can_auto_confirm(
    method: ResolutionMethod,
    *,
    conflicts: tuple[UUID, ...] = (),
) -> bool:
    return method in _AUTO_CONFIRM_METHODS and not conflicts


def _normalize_reasons(values: tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        reason = value.strip()
        if not reason:
            continue
        if len(reason) > 500:
            raise ValueError("resolution reason cannot exceed 500 characters")
        key = reason.casefold()
        if key not in seen:
            seen.add(key)
            normalized.append(reason)
    return tuple(normalized)


def _required_text(value: str, name: str, maximum: int) -> None:
    if not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must be between 1 and {maximum} characters")

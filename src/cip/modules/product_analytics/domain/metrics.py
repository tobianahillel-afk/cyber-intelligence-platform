from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import fmean
from uuid import UUID

from cip.shared.kernel.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class OpportunityOutcome:
    opportunity_id: UUID
    score: float
    accepted: bool
    false_positive: bool
    source_published_at: datetime
    detected_at: datetime
    reviewed_at: datetime
    processing_cost_eur: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 100.0:
            raise ValueError("score must be between 0 and 100")
        if self.processing_cost_eur < 0:
            raise ValueError("processing_cost_eur cannot be negative")
        for field_name in ("source_published_at", "detected_at", "reviewed_at"):
            object.__setattr__(
                self,
                field_name,
                require_aware_utc(getattr(self, field_name), field_name=field_name),
            )
        if self.detected_at < self.source_published_at:
            raise ValueError("detected_at cannot precede source_published_at")
        if self.reviewed_at < self.detected_at:
            raise ValueError("reviewed_at cannot precede detected_at")
        if self.accepted and self.false_positive:
            raise ValueError("an accepted opportunity cannot be a false positive")


def precision_at_k(outcomes: tuple[OpportunityOutcome, ...], k: int) -> float:
    if k < 1:
        raise ValueError("k must be positive")
    if not outcomes:
        return 0.0
    ranked = sorted(outcomes, key=lambda item: item.score, reverse=True)[:k]
    return sum(item.accepted for item in ranked) / len(ranked)


def acceptance_rate(outcomes: tuple[OpportunityOutcome, ...]) -> float:
    if not outcomes:
        return 0.0
    return sum(item.accepted for item in outcomes) / len(outcomes)


def false_positive_rate(outcomes: tuple[OpportunityOutcome, ...]) -> float:
    if not outcomes:
        return 0.0
    return sum(item.false_positive for item in outcomes) / len(outcomes)


def mean_detection_latency_seconds(outcomes: tuple[OpportunityOutcome, ...]) -> float:
    if not outcomes:
        return 0.0
    return fmean(
        (item.detected_at - item.source_published_at).total_seconds() for item in outcomes
    )


def cost_per_accepted_opportunity(outcomes: tuple[OpportunityOutcome, ...]) -> float | None:
    accepted_count = sum(item.accepted for item in outcomes)
    if accepted_count == 0:
        return None
    return sum(item.processing_cost_eur for item in outcomes) / accepted_count

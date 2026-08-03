from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cip.modules.product_analytics.domain.metrics import (
    OpportunityOutcome,
    acceptance_rate,
    cost_per_accepted_opportunity,
    false_positive_rate,
    mean_detection_latency_seconds,
    precision_at_k,
)

NOW = datetime(2026, 8, 3, 16, 0, tzinfo=UTC)


def outcome(
    score: float,
    *,
    accepted: bool,
    false_positive: bool = False,
    latency_minutes: int = 10,
    cost: float = 5.0,
) -> OpportunityOutcome:
    published = NOW
    detected = published + timedelta(minutes=latency_minutes)
    return OpportunityOutcome(
        opportunity_id=uuid4(),
        score=score,
        accepted=accepted,
        false_positive=false_positive,
        source_published_at=published,
        detected_at=detected,
        reviewed_at=detected + timedelta(minutes=5),
        processing_cost_eur=cost,
    )


def test_quality_metrics_are_calculated_from_reviewed_outcomes() -> None:
    outcomes = (
        outcome(95, accepted=True, latency_minutes=5, cost=10),
        outcome(80, accepted=False, false_positive=True, latency_minutes=15, cost=5),
        outcome(70, accepted=True, latency_minutes=10, cost=5),
    )

    assert precision_at_k(outcomes, 2) == 0.5
    assert acceptance_rate(outcomes) == pytest.approx(2 / 3)
    assert false_positive_rate(outcomes) == pytest.approx(1 / 3)
    assert mean_detection_latency_seconds(outcomes) == 600.0
    assert cost_per_accepted_opportunity(outcomes) == 10.0


def test_empty_metric_sets_have_safe_results() -> None:
    assert precision_at_k((), 10) == 0.0
    assert acceptance_rate(()) == 0.0
    assert false_positive_rate(()) == 0.0
    assert mean_detection_latency_seconds(()) == 0.0
    assert cost_per_accepted_opportunity(()) is None


def test_precision_requires_positive_k() -> None:
    with pytest.raises(ValueError, match="k must be positive"):
        precision_at_k((), 0)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"score": -1}, "score"),
        ({"score": 101}, "score"),
        ({"processing_cost_eur": -1}, "cannot be negative"),
        ({"source_published_at": datetime(2026, 8, 3)}, "timezone-aware"),
        ({"detected_at": NOW - timedelta(seconds=1)}, "detected_at cannot precede"),
        ({"reviewed_at": NOW - timedelta(seconds=1)}, "reviewed_at cannot precede"),
        ({"accepted": True, "false_positive": True}, "cannot be a false positive"),
    ],
)
def test_outcome_validation(changes: dict[str, object], message: str) -> None:
    published = NOW
    detected = NOW + timedelta(minutes=1)
    values: dict[str, object] = {
        "opportunity_id": uuid4(),
        "score": 50.0,
        "accepted": False,
        "false_positive": False,
        "source_published_at": published,
        "detected_at": detected,
        "reviewed_at": detected + timedelta(minutes=1),
        "processing_cost_eur": 1.0,
    }
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        OpportunityOutcome(**values)  # type: ignore[arg-type]

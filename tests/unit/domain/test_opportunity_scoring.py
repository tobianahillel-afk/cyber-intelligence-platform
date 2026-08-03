from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cip.modules.opportunities.domain.scoring import (
    ComponentKind,
    OpportunityComponent,
    OpportunityScore,
)

NOW = datetime(2026, 8, 3, 16, 0, tzinfo=UTC)
LATER = NOW + timedelta(days=1)


def test_score_is_computed_bounded_and_hashed() -> None:
    positive = OpportunityComponent(
        rule_id="confirmed-incident",
        value=1.0,
        weight=80.0,
        reason="Confirmed incident",
    )
    additional = OpportunityComponent(
        rule_id="public-tender",
        value=1.0,
        weight=40.0,
        reason="Public tender",
    )
    penalty = OpportunityComponent(
        rule_id="stale-data",
        value=0.5,
        weight=20.0,
        reason="Old supporting evidence",
        kind=ComponentKind.PENALTY,
    )
    score = OpportunityScore(
        organization_id=uuid4(),
        score_version="1",
        config_version="2026-08-03",
        components=(positive, additional, penalty),
        generated_at=NOW,
        expires_at=LATER,
    )

    assert positive.contribution == 80.0
    assert penalty.contribution == -10.0
    assert score.raw_score == 110.0
    assert score.adjusted_score == 100.0
    assert len(score.calculation_hash) == 64


def test_score_hash_is_independent_from_generation_time() -> None:
    organization_id = uuid4()
    component = OpportunityComponent(
        rule_id="signal",
        value=0.5,
        weight=40.0,
        reason="Signal",
        evidence_ids=(uuid4(),),
    )
    first = OpportunityScore(organization_id, "1", "1", (component,), generated_at=NOW)
    second = OpportunityScore(organization_id, "1", "1", (component,), generated_at=LATER)

    assert first.calculation_hash == second.calculation_hash
    assert first.adjusted_score == 20.0


def test_penalties_cannot_produce_negative_adjusted_score() -> None:
    penalty = OpportunityComponent(
        rule_id="weak-source",
        value=1.0,
        weight=50.0,
        reason="Weak source",
        kind=ComponentKind.PENALTY,
    )
    score = OpportunityScore(uuid4(), "1", "1", (penalty,), generated_at=NOW)

    assert score.raw_score == -50.0
    assert score.adjusted_score == 0.0


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"rule_id": ""}, "rule_id"),
        ({"reason": ""}, "reason"),
        ({"value": -0.1}, "value"),
        ({"value": 1.1}, "value"),
        ({"weight": -1.0}, "weight"),
        ({"weight": 101.0}, "weight"),
    ],
)
def test_component_rejects_invalid_values(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "rule_id": "rule",
        "value": 0.5,
        "weight": 10.0,
        "reason": "Reason",
    }
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        OpportunityComponent(**values)  # type: ignore[arg-type]


def test_score_rejects_invalid_versions_and_dates() -> None:
    with pytest.raises(ValueError, match="score_version"):
        OpportunityScore(uuid4(), "", "config", (), generated_at=NOW)
    with pytest.raises(ValueError, match="generated_at must be timezone-aware"):
        OpportunityScore(uuid4(), "1", "1", (), generated_at=datetime(2026, 8, 3))
    with pytest.raises(ValueError, match="later than generated_at"):
        OpportunityScore(uuid4(), "1", "1", (), generated_at=NOW, expires_at=NOW)

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cip.modules.opportunities.domain.entities import (
    CommercialSignal,
    DataQuality,
    NeedHypothesis,
    Opportunity,
    OpportunityFamily,
    OpportunityState,
    ReviewAction,
    SignalType,
)
from cip.modules.opportunities.domain.rules import (
    SiemSocRuleConfig,
    evaluate_siem_soc_buying_intent,
)
from cip.modules.opportunities.domain.scoring import OpportunityComponent, OpportunityScore

NOW = datetime(2026, 8, 4, 0, 0, tzinfo=UTC)


def test_commercial_signal_normalizes_terms_and_builds_stable_key() -> None:
    organization_id = uuid4()
    evidence_id = uuid4()
    signal = CommercialSignal(
        organization_id=organization_id,
        evidence_id=evidence_id,
        signal_type=SignalType.PUBLIC_TENDER,
        title="  SIEM tender  ",
        summary="Managed SOC procurement",
        confidence=0.8,
        matched_terms=(" SIEM ", "siem", "SOC"),
        published_at=NOW - timedelta(hours=1),
        collected_at=NOW,
    )
    duplicate = CommercialSignal(
        organization_id=organization_id,
        evidence_id=evidence_id,
        signal_type=SignalType.PUBLIC_TENDER,
        title="Other title",
        summary="Other summary",
        confidence=0.2,
        collected_at=NOW,
    )

    assert signal.title == "SIEM tender"
    assert signal.matched_terms == ("siem", "soc")
    assert signal.effective_at == NOW - timedelta(hours=1)
    assert signal.idempotency_key == duplicate.idempotency_key


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"title": " "}, "title"),
        ({"summary": " "}, "summary"),
        ({"confidence": 1.1}, "confidence"),
        ({"collected_at": datetime(2026, 8, 4)}, "timezone-aware"),
        ({"expires_at": NOW}, "later than collected_at"),
    ],
)
def test_commercial_signal_rejects_invalid_values(
    changes: dict[str, object],
    message: str,
) -> None:
    values: dict[str, object] = {
        "organization_id": uuid4(),
        "evidence_id": uuid4(),
        "signal_type": SignalType.JOB_POSTING,
        "title": "SOC analyst",
        "summary": "Hiring for security operations",
        "confidence": 0.7,
        "collected_at": NOW,
        "expires_at": NOW + timedelta(days=1),
    }
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        CommercialSignal(**values)  # type: ignore[arg-type]


def test_need_hypothesis_deduplicates_links_and_builds_stable_key() -> None:
    organization_id = uuid4()
    signal_id = uuid4()
    evidence_id = uuid4()
    hypothesis = NeedHypothesis(
        organization_id=organization_id,
        family=OpportunityFamily.SIEM_SOC_BUYING_INTENT,
        rule_id="rule",
        rule_version="1",
        rationale="Public buying intent",
        signal_ids=(signal_id, signal_id),
        evidence_ids=(evidence_id, evidence_id),
        generated_at=NOW,
        expires_at=NOW + timedelta(days=30),
    )

    assert hypothesis.signal_ids == (signal_id,)
    assert hypothesis.evidence_ids == (evidence_id,)
    assert len(hypothesis.idempotency_key) == 64


@pytest.mark.parametrize(
    "changes",
    [
        {"rule_id": ""},
        {"rationale": ""},
        {"signal_ids": ()},
        {"evidence_ids": ()},
        {"expires_at": NOW},
    ],
)
def test_need_hypothesis_rejects_invalid_values(changes: dict[str, object]) -> None:
    values: dict[str, object] = {
        "organization_id": uuid4(),
        "family": OpportunityFamily.SIEM_SOC_BUYING_INTENT,
        "rule_id": "rule",
        "rule_version": "1",
        "rationale": "Rationale",
        "signal_ids": (uuid4(),),
        "evidence_ids": (uuid4(),),
        "generated_at": NOW,
        "expires_at": NOW + timedelta(days=1),
    }
    values.update(changes)

    with pytest.raises(ValueError):
        NeedHypothesis(**values)  # type: ignore[arg-type]


def test_opportunity_review_lifecycle() -> None:
    opportunity = _opportunity()

    qualified = opportunity.review(
        ReviewAction.QUALIFY,
        now=NOW + timedelta(minutes=1),
        note="Validated",
    )
    rejected = qualified.review(
        ReviewAction.REJECT,
        now=NOW + timedelta(minutes=2),
        note="Not a fit",
    )
    snoozed = rejected.review(
        ReviewAction.SNOOZE,
        now=NOW + timedelta(minutes=3),
        snoozed_until=NOW + timedelta(days=3),
    )
    enrichment = snoozed.review(
        ReviewAction.REQUEST_ENRICHMENT,
        now=NOW + timedelta(minutes=4),
    )
    reopened = enrichment.review(
        ReviewAction.REOPEN,
        now=NOW + timedelta(minutes=5),
    )

    assert qualified.state is OpportunityState.QUALIFIED
    assert rejected.rejected_reason == "Not a fit"
    assert snoozed.state is OpportunityState.SNOOZED
    assert snoozed.snoozed_until == NOW + timedelta(days=3)
    assert enrichment.state is OpportunityState.ENRICHMENT_REQUESTED
    assert reopened.state is OpportunityState.NEEDS_REVIEW


def test_opportunity_review_requires_reject_reason_and_future_snooze() -> None:
    opportunity = _opportunity()

    with pytest.raises(ValueError, match="reject requires"):
        opportunity.review(ReviewAction.REJECT, now=NOW)
    with pytest.raises(ValueError, match="requires snoozed_until"):
        opportunity.review(ReviewAction.SNOOZE, now=NOW)
    with pytest.raises(ValueError, match="later than now"):
        opportunity.review(ReviewAction.SNOOZE, now=NOW, snoozed_until=NOW)


def test_rule_returns_complete_explainable_opportunity() -> None:
    organization_id = uuid4()
    tender = _signal(
        organization_id,
        SignalType.PUBLIC_TENDER,
        title="SIEM and SOC public tender",
        evidence_id=uuid4(),
        confidence=0.9,
    )
    job = _signal(
        organization_id,
        SignalType.JOB_POSTING,
        title="SOC analyst using Microsoft Sentinel",
        evidence_id=uuid4(),
        confidence=0.8,
    )

    evaluation = evaluate_siem_soc_buying_intent(
        organization_id,
        (tender, job),
        now=NOW,
    )

    assert evaluation is not None
    assert evaluation.opportunity.data_quality is DataQuality.COMPLETE
    assert evaluation.opportunity.score.adjusted_score > 80
    assert evaluation.opportunity.confidence == 0.85
    assert evaluation.opportunity.next_action.startswith("Review tender")
    assert evaluation.opportunity.created_at == NOW
    assert evaluation.opportunity.updated_at == NOW
    assert len(evaluation.hypothesis.evidence_ids) == 2
    assert {item.rule_id for item in evaluation.opportunity.score.components} == {
        "public-tender-intent",
        "security-operations-hiring",
        "cross-source-corroboration",
        "signal-freshness",
        "evidence-confidence",
        "single-source-penalty",
    }


def test_rule_marks_single_source_as_partial_and_penalized() -> None:
    organization_id = uuid4()
    job = _signal(
        organization_id,
        SignalType.JOB_POSTING,
        title="Hiring a Splunk SIEM engineer",
        evidence_id=uuid4(),
        confidence=0.7,
    )

    evaluation = evaluate_siem_soc_buying_intent(organization_id, (job,), now=NOW)

    assert evaluation is not None
    assert evaluation.opportunity.data_quality is DataQuality.PARTIAL
    penalty = next(
        item
        for item in evaluation.opportunity.score.components
        if item.rule_id == "single-source-penalty"
    )
    assert penalty.contribution < 0
    assert evaluation.opportunity.next_action.startswith("Validate hiring")


def test_rule_ignores_wrong_organization_stale_expired_and_unmatched_signals() -> None:
    organization_id = uuid4()
    signals = (
        _signal(uuid4(), SignalType.PUBLIC_TENDER, title="SIEM tender"),
        _signal(
            organization_id,
            SignalType.PUBLIC_TENDER,
            title="SIEM tender",
            published_at=NOW - timedelta(days=91),
        ),
        _signal(
            organization_id,
            SignalType.PUBLIC_TENDER,
            title="SIEM tender",
            published_at=NOW - timedelta(days=1),
            collected_at=NOW - timedelta(days=1),
            expires_at=NOW - timedelta(seconds=1),
        ),
        _signal(
            organization_id,
            SignalType.PUBLIC_TENDER,
            title="Office furniture tender",
        ),
    )

    assert evaluate_siem_soc_buying_intent(organization_id, signals, now=NOW) is None


@pytest.mark.parametrize(
    "changes",
    [
        {"rule_id": ""},
        {"signal_window_days": 0},
        {"opportunity_ttl_days": 0},
    ],
)
def test_rule_config_rejects_invalid_values(changes: dict[str, object]) -> None:
    values: dict[str, object] = {
        "rule_id": "rule",
        "rule_version": "1",
        "signal_window_days": 90,
        "opportunity_ttl_days": 30,
    }
    values.update(changes)

    with pytest.raises(ValueError):
        SiemSocRuleConfig(**values)  # type: ignore[arg-type]


def _signal(
    organization_id: object,
    signal_type: SignalType,
    *,
    title: str,
    evidence_id: object | None = None,
    confidence: float = 0.8,
    published_at: datetime | None = None,
    collected_at: datetime = NOW,
    expires_at: datetime | None = None,
) -> CommercialSignal:
    return CommercialSignal(
        organization_id=organization_id,  # type: ignore[arg-type]
        evidence_id=evidence_id or uuid4(),  # type: ignore[arg-type]
        signal_type=signal_type,
        title=title,
        summary=title,
        confidence=confidence,
        published_at=published_at or NOW - timedelta(hours=1),
        collected_at=collected_at,
        expires_at=expires_at,
    )


def _opportunity() -> Opportunity:
    organization_id = uuid4()
    score = OpportunityScore(
        organization_id=organization_id,
        score_version="1",
        config_version="config",
        components=(
            OpportunityComponent(
                rule_id="component",
                value=0.8,
                weight=50,
                reason="Evidence-backed signal",
            ),
        ),
        generated_at=NOW,
        expires_at=NOW + timedelta(days=30),
    )
    return Opportunity(
        organization_id=organization_id,
        hypothesis_id=uuid4(),
        recommended_offer="SIEM assessment",
        relevant_roles=("RSSI",),
        trigger_summary="Buying intent",
        next_action="Review evidence",
        score=score,
        confidence=0.8,
        last_evidence_at=NOW,
        data_quality=DataQuality.COMPLETE,
        created_at=NOW,
        updated_at=NOW,
    )

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from cip.modules.opportunities.domain.entities import (
    CommercialSignal,
    NeedHypothesisClass,
    NeedUrgency,
    SignalPolarity,
    SignalType,
)
from cip.modules.opportunities.domain.fusion import FusionConfig, fuse_need_hypotheses
from cip.modules.service_taxonomy.domain.models import CyberServiceFamily

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
ORG_ID = uuid4()


def test_two_independent_sources_can_fuse_every_service_family() -> None:
    signals: list[CommercialSignal] = []
    for family in CyberServiceFamily:
        signals.extend(
            (
                _signal(family, source="one", confidence=0.82),
                _signal(family, source="two", confidence=0.78),
            )
        )

    hypotheses = fuse_need_hypotheses(ORG_ID, tuple(signals), now=NOW)

    assert len(hypotheses) == 19
    assert {item.service_families[0] for item in hypotheses} == set(CyberServiceFamily)
    assert all(item.confidence > 0.58 for item in hypotheses)


def test_two_independent_sources_preserve_every_need_hypothesis_class() -> None:
    for hypothesis_class in NeedHypothesisClass:
        signals = (
            _signal(
                CyberServiceFamily.GRC_COMPLIANCE,
                source="one",
                confidence=0.82,
                hypothesis_class=hypothesis_class,
            ),
            _signal(
                CyberServiceFamily.GRC_COMPLIANCE,
                source="two",
                confidence=0.80,
                hypothesis_class=hypothesis_class,
            ),
        )

        hypothesis = fuse_need_hypotheses(ORG_ID, signals, now=NOW)[0]

        assert hypothesis.hypothesis_class is hypothesis_class


def test_single_weak_nonexplicit_signal_is_research_only_and_capped() -> None:
    hypothesis = fuse_need_hypotheses(
        ORG_ID,
        (_signal(CyberServiceFamily.CLOUD_SECURITY, confidence=0.60),),
        now=NOW,
    )[0]

    assert hypothesis.hypothesis_class is NeedHypothesisClass.RESEARCH_ONLY_WEAK_SIGNAL
    assert hypothesis.confidence <= 0.58
    assert hypothesis.urgency is NeedUrgency.LOW


def test_single_explicit_procurement_can_remain_an_explicit_need() -> None:
    hypothesis = fuse_need_hypotheses(
        ORG_ID,
        (
            _signal(
                CyberServiceFamily.PENETRATION_TESTING,
                confidence=0.90,
                hypothesis_class=NeedHypothesisClass.EXPLICIT_PROCUREMENT,
                explicit=True,
                signal_type=SignalType.PUBLIC_TENDER,
            ),
        ),
        now=NOW,
    )[0]

    assert hypothesis.hypothesis_class is NeedHypothesisClass.EXPLICIT_PROCUREMENT
    assert hypothesis.urgency is NeedUrgency.HIGH
    assert hypothesis.confidence > 0.90


def test_duplicate_corroboration_group_does_not_count_as_independent_support() -> None:
    one = _signal(CyberServiceFamily.GRC_COMPLIANCE, source="publisher-a", confidence=0.80)
    duplicate = _signal(
        CyberServiceFamily.GRC_COMPLIANCE,
        source="publisher-b",
        confidence=0.78,
        corroboration_group="syndicated-story-1",
    )
    one_grouped = _replace_corroboration(one, "syndicated-story-1")
    independent = _signal(
        CyberServiceFamily.GRC_COMPLIANCE,
        source="publisher-c",
        confidence=0.78,
    )

    duplicate_hypothesis = fuse_need_hypotheses(
        ORG_ID, (one_grouped, duplicate), now=NOW
    )[0]
    independent_hypothesis = fuse_need_hypotheses(
        ORG_ID, (one, independent), now=NOW
    )[0]

    assert duplicate_hypothesis.confidence <= 0.58
    assert independent_hypothesis.confidence > duplicate_hypothesis.confidence


def test_contradiction_and_negative_evidence_reduce_confidence() -> None:
    support = (
        _signal(CyberServiceFamily.IAM_PAM_ZERO_TRUST, source="one", confidence=0.86),
        _signal(CyberServiceFamily.IAM_PAM_ZERO_TRUST, source="two", confidence=0.82),
    )
    baseline = fuse_need_hypotheses(ORG_ID, support, now=NOW)[0]
    contested = fuse_need_hypotheses(
        ORG_ID,
        (
            *support,
            _signal(
                CyberServiceFamily.IAM_PAM_ZERO_TRUST,
                source="three",
                confidence=0.90,
                polarity=SignalPolarity.CONTRADICTING,
            ),
            _signal(
                CyberServiceFamily.IAM_PAM_ZERO_TRUST,
                source="four",
                confidence=0.70,
                polarity=SignalPolarity.NEGATIVE,
            ),
        ),
        now=NOW,
    )[0]

    assert contested.confidence < baseline.confidence
    assert len(contested.conflicting_signal_ids) == 1
    assert len(contested.negative_signal_ids) == 1


def test_negative_only_evidence_never_creates_a_need_hypothesis() -> None:
    signal = _signal(
        CyberServiceFamily.NETWORK_SECURITY_SASE,
        polarity=SignalPolarity.NEGATIVE,
        confidence=0.95,
    )

    assert fuse_need_hypotheses(ORG_ID, (signal,), now=NOW) == ()


def test_historical_incident_does_not_create_current_incident_urgency() -> None:
    hypothesis = fuse_need_hypotheses(
        ORG_ID,
        (
            _signal(
                CyberServiceFamily.INCIDENT_RESPONSE_DFIR,
                hypothesis_class=NeedHypothesisClass.INCIDENT_URGENCY,
                signal_type=SignalType.INCIDENT,
                confidence=0.95,
                explicit=True,
                historical=True,
            ),
        ),
        now=NOW,
    )[0]

    assert hypothesis.hypothesis_class is NeedHypothesisClass.RESEARCH_ONLY_WEAK_SIGNAL
    assert hypothesis.confidence <= 0.45
    assert hypothesis.urgency is NeedUrgency.LOW


def test_global_vulnerability_without_org_applicability_is_ignored() -> None:
    other_organization = uuid4()
    signal = CommercialSignal(
        organization_id=other_organization,
        evidence_id=uuid4(),
        signal_type=SignalType.VULNERABILITY_APPLICABILITY,
        title="Global CVE metadata only",
        summary="No organization-specific applicability has been established.",
        confidence=0.99,
        collected_at=NOW,
        service_families=(CyberServiceFamily.VULNERABILITY_MANAGEMENT_ASM,),
        hypothesis_classes=(NeedHypothesisClass.TECHNOLOGY_RISK_LIFECYCLE,),
        independence_key="global-cve-source",
        mapping_rule_id="test-map",
        mapping_rule_version="1.0.0",
    )

    assert fuse_need_hypotheses(ORG_ID, (signal,), now=NOW) == ()


def test_expired_signal_is_ignored() -> None:
    signal = _signal(
        CyberServiceFamily.CYBER_INSURANCE_READINESS,
        expires_at=NOW - timedelta(seconds=1),
    )

    assert fuse_need_hypotheses(ORG_ID, (signal,), now=NOW) == ()


def test_research_discovery_stays_weak_even_with_high_confidence() -> None:
    hypothesis = fuse_need_hypotheses(
        ORG_ID,
        (
            _signal(
                CyberServiceFamily.DATA_SECURITY_PRIVACY,
                signal_type=SignalType.RESEARCH_DISCOVERY,
                confidence=0.99,
            ),
        ),
        now=NOW,
    )[0]

    assert hypothesis.hypothesis_class is NeedHypothesisClass.RESEARCH_ONLY_WEAK_SIGNAL
    assert hypothesis.confidence <= 0.40


def test_multi_service_signal_yields_separate_need_tracks() -> None:
    signal = _signal(
        CyberServiceFamily.CLOUD_SECURITY,
        second_family=CyberServiceFamily.APPLICATION_SECURITY_DEVSECOPS,
        hypothesis_class=NeedHypothesisClass.EXPLICIT_PROCUREMENT,
        explicit=True,
        signal_type=SignalType.PUBLIC_TENDER,
        confidence=0.9,
    )

    hypotheses = fuse_need_hypotheses(ORG_ID, (signal,), now=NOW)

    assert {item.service_families[0] for item in hypotheses} == {
        CyberServiceFamily.CLOUD_SECURITY,
        CyberServiceFamily.APPLICATION_SECURITY_DEVSECOPS,
    }


def test_rule_version_changes_hypothesis_identity_for_replay() -> None:
    signals = (
        _signal(CyberServiceFamily.OT_ICS_IOT_SECURITY, source="one", confidence=0.8),
        _signal(CyberServiceFamily.OT_ICS_IOT_SECURITY, source="two", confidence=0.8),
    )
    first = fuse_need_hypotheses(
        ORG_ID, signals, now=NOW, config=FusionConfig(rule_version="1.0.0")
    )[0]
    second = fuse_need_hypotheses(
        ORG_ID, signals, now=NOW, config=FusionConfig(rule_version="1.1.0")
    )[0]

    assert first.idempotency_key != second.idempotency_key


def _signal(
    family: CyberServiceFamily,
    *,
    source: str = "source-a",
    confidence: float = 0.7,
    hypothesis_class: NeedHypothesisClass = NeedHypothesisClass.CAPABILITY_GAP,
    polarity: SignalPolarity = SignalPolarity.SUPPORTING,
    signal_type: SignalType = SignalType.CORPORATE_CHANGE,
    explicit: bool = False,
    historical: bool = False,
    corroboration_group: str | None = None,
    second_family: CyberServiceFamily | None = None,
    expires_at: datetime | None = None,
) -> CommercialSignal:
    evidence_id = uuid4()
    families = (family,) if second_family is None else (family, second_family)
    return CommercialSignal(
        organization_id=ORG_ID,
        evidence_id=evidence_id,
        signal_type=signal_type,
        title=f"Signal for {family.value}",
        summary="Canonical evidence-derived signal.",
        confidence=confidence,
        collected_at=NOW - timedelta(days=5),
        published_at=NOW - timedelta(days=6),
        expires_at=expires_at,
        service_families=families,
        hypothesis_classes=(hypothesis_class,),
        independence_key=f"source:{source}",
        corroboration_group_key=corroboration_group,
        polarity=polarity,
        is_explicit=explicit,
        historical_only=historical,
        mapping_rule_id="test-map",
        mapping_rule_version="1.0.0",
    )


def _replace_corroboration(signal: CommercialSignal, value: str) -> CommercialSignal:
    return CommercialSignal(
        organization_id=signal.organization_id,
        evidence_id=signal.evidence_id,
        signal_type=signal.signal_type,
        title=signal.title,
        summary=signal.summary,
        confidence=signal.confidence,
        collected_at=signal.collected_at,
        id=signal.id,
        published_at=signal.published_at,
        expires_at=signal.expires_at,
        created_at=signal.created_at,
        service_families=signal.service_families,
        hypothesis_classes=signal.hypothesis_classes,
        independence_key=signal.independence_key,
        corroboration_group_key=value,
        polarity=signal.polarity,
        is_explicit=signal.is_explicit,
        historical_only=signal.historical_only,
        mapping_rule_id=signal.mapping_rule_id,
        mapping_rule_version=signal.mapping_rule_version,
    )

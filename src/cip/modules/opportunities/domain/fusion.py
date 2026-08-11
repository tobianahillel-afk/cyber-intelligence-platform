from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from cip.modules.opportunities.domain.entities import (
    CommercialSignal,
    NeedHorizon,
    NeedHypothesis,
    NeedHypothesisClass,
    NeedUrgency,
    OpportunityFamily,
    SignalPolarity,
    SignalType,
    SourceContribution,
)
from cip.modules.service_taxonomy.domain.catalog import applicable_offers
from cip.modules.service_taxonomy.domain.models import CyberServiceFamily
from cip.shared.kernel.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class FusionConfig:
    rule_id: str = "lot24-need-fusion"
    rule_version: str = "1.0.0"
    weak_confidence_cap: float = 0.58
    historical_confidence_cap: float = 0.45
    research_confidence_cap: float = 0.40

    def __post_init__(self) -> None:
        if not self.rule_id.strip() or not self.rule_version.strip():
            raise ValueError("fusion rule id and version are required")
        for field_name in (
            "weak_confidence_cap",
            "historical_confidence_cap",
            "research_confidence_cap",
        ):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class _FusionKey:
    hypothesis_class: NeedHypothesisClass
    service_family: CyberServiceFamily


@dataclass(frozen=True, slots=True)
class _FusionEvidence:
    supporting: tuple[CommercialSignal, ...]
    contradicting: tuple[CommercialSignal, ...]
    negative: tuple[CommercialSignal, ...]


DEFAULT_FUSION_CONFIG = FusionConfig()


def fuse_need_hypotheses(
    organization_id: UUID,
    signals: tuple[CommercialSignal, ...],
    *,
    now: datetime,
    config: FusionConfig = DEFAULT_FUSION_CONFIG,
) -> tuple[NeedHypothesis, ...]:
    evaluated_at = require_aware_utc(now, field_name="now")
    groups: dict[_FusionKey, list[CommercialSignal]] = defaultdict(list)
    for signal in signals:
        if not _eligible(signal, organization_id=organization_id, now=evaluated_at):
            continue
        for hypothesis_class in signal.hypothesis_classes:
            for family in signal.service_families:
                groups[_FusionKey(hypothesis_class, family)].append(signal)
    hypotheses: list[NeedHypothesis] = []
    for key, grouped in groups.items():
        grouped_signals = tuple(grouped)
        if not _partition(grouped_signals).supporting:
            continue
        hypotheses.append(
            _fuse_group(
                organization_id,
                key,
                grouped_signals,
                now=evaluated_at,
                config=config,
            )
        )
    return tuple(
        sorted(
            hypotheses,
            key=lambda item: (
                item.service_families[0].value,
                item.hypothesis_class.value,
            ),
        )
    )


def _eligible(signal: CommercialSignal, *, organization_id: UUID, now: datetime) -> bool:
    return (
        signal.organization_id == organization_id
        and bool(signal.service_families)
        and bool(signal.hypothesis_classes)
        and (signal.expires_at is None or signal.expires_at > now)
    )


def _fuse_group(
    organization_id: UUID,
    key: _FusionKey,
    signals: tuple[CommercialSignal, ...],
    *,
    now: datetime,
    config: FusionConfig,
) -> NeedHypothesis:
    evidence = _partition(signals)
    support = _deduplicate_correlated(evidence.supporting)
    effective_class = _effective_class(key.hypothesis_class, support)
    confidence = _confidence(evidence, support, now=now, config=config)
    urgency, horizon = _timing(effective_class)
    expires_at = _hypothesis_expiry(signals, now=now, horizon=horizon)
    supporting_ids = tuple(signal.id for signal in evidence.supporting)
    evidence_ids = tuple(dict.fromkeys(signal.evidence_id for signal in signals))
    return NeedHypothesis(
        organization_id=organization_id,
        family=OpportunityFamily.CYBER_SERVICE_NEED,
        rule_id=config.rule_id,
        rule_version=config.rule_version,
        rationale=_rationale(
            key.service_family,
            effective_class,
            evidence,
            independent_support_count=len(support),
            confidence=confidence,
        ),
        signal_ids=supporting_ids,
        evidence_ids=evidence_ids,
        generated_at=now,
        expires_at=expires_at,
        hypothesis_class=effective_class,
        service_families=(key.service_family,),
        confidence=confidence,
        urgency=urgency,
        horizon=horizon,
        applicable_offers=applicable_offers((key.service_family,)),
        conflicting_signal_ids=tuple(signal.id for signal in evidence.contradicting),
        negative_signal_ids=tuple(signal.id for signal in evidence.negative),
        source_contributions=_source_contributions(signals, now=now),
    )


def _partition(signals: tuple[CommercialSignal, ...]) -> _FusionEvidence:
    return _FusionEvidence(
        supporting=tuple(
            signal for signal in signals if signal.polarity is SignalPolarity.SUPPORTING
        ),
        contradicting=tuple(
            signal for signal in signals if signal.polarity is SignalPolarity.CONTRADICTING
        ),
        negative=tuple(
            signal for signal in signals if signal.polarity is SignalPolarity.NEGATIVE
        ),
    )


def _deduplicate_correlated(
    signals: tuple[CommercialSignal, ...],
) -> tuple[CommercialSignal, ...]:
    strongest: dict[str, CommercialSignal] = {}
    for signal in signals:
        current = strongest.get(signal.corroboration_key)
        if current is None or signal.confidence > current.confidence:
            strongest[signal.corroboration_key] = signal
    return tuple(strongest[key] for key in sorted(strongest))


def _effective_class(
    requested: NeedHypothesisClass,
    support: tuple[CommercialSignal, ...],
) -> NeedHypothesisClass:
    if not support:
        return NeedHypothesisClass.RESEARCH_ONLY_WEAK_SIGNAL
    if all(signal.historical_only for signal in support):
        return NeedHypothesisClass.RESEARCH_ONLY_WEAK_SIGNAL
    independent = len(support)
    explicit = any(signal.is_explicit for signal in support)
    strongest = max(signal.confidence for signal in support)
    research_only = all(
        signal.signal_type is SignalType.RESEARCH_DISCOVERY for signal in support
    )
    if research_only or (independent < 2 and not explicit and strongest < 0.75):
        return NeedHypothesisClass.RESEARCH_ONLY_WEAK_SIGNAL
    return requested


def _confidence(
    evidence: _FusionEvidence,
    independent_support: tuple[CommercialSignal, ...],
    *,
    now: datetime,
    config: FusionConfig,
) -> float:
    if not independent_support:
        return 0.0
    support_scores = [
        signal.confidence * _freshness(signal, now=now) for signal in independent_support
    ]
    score = max(support_scores)
    score += min(0.16, max(0, len(independent_support) - 1) * 0.08)
    if any(signal.is_explicit for signal in independent_support):
        score += 0.12
    score -= _negative_penalty(evidence.contradicting, scale=0.40)
    score -= _negative_penalty(evidence.negative, scale=0.30)
    score = _clamp(score)
    if len(independent_support) == 1 and not independent_support[0].is_explicit:
        score = min(score, config.weak_confidence_cap)
    if all(signal.historical_only for signal in independent_support):
        score = min(score, config.historical_confidence_cap)
    if all(
        signal.signal_type is SignalType.RESEARCH_DISCOVERY
        for signal in independent_support
    ):
        score = min(score, config.research_confidence_cap)
    return round(score, 4)


def _freshness(signal: CommercialSignal, *, now: datetime) -> float:
    age = max(timedelta(0), now - signal.effective_at)
    days = age.total_seconds() / 86_400
    if days <= 30:
        return 1.0
    if days <= 90:
        return 0.9
    if days <= 180:
        return 0.75
    if days <= 365:
        return 0.55
    return 0.35


def _negative_penalty(signals: tuple[CommercialSignal, ...], *, scale: float) -> float:
    if not signals:
        return 0.0
    strongest = max(signal.confidence for signal in _deduplicate_correlated(signals))
    return strongest * scale


def _timing(hypothesis_class: NeedHypothesisClass) -> tuple[NeedUrgency, NeedHorizon]:
    if hypothesis_class is NeedHypothesisClass.INCIDENT_URGENCY:
        return NeedUrgency.IMMEDIATE, NeedHorizon.IMMEDIATE
    if hypothesis_class in {
        NeedHypothesisClass.EXPLICIT_PROCUREMENT,
        NeedHypothesisClass.CONTRACT_RENEWAL_REPLACEMENT,
        NeedHypothesisClass.REGULATORY_DEADLINE_GAP,
    }:
        return NeedUrgency.HIGH, NeedHorizon.NEAR_TERM
    if hypothesis_class in {
        NeedHypothesisClass.TECHNOLOGY_RISK_LIFECYCLE,
        NeedHypothesisClass.EXTERNAL_EXPOSURE,
        NeedHypothesisClass.PROVIDER_DISSATISFACTION_TRANSITION,
    }:
        return NeedUrgency.MEDIUM, NeedHorizon.NEAR_TERM
    if hypothesis_class is NeedHypothesisClass.RESEARCH_ONLY_WEAK_SIGNAL:
        return NeedUrgency.LOW, NeedHorizon.LONG_TERM
    return NeedUrgency.MEDIUM, NeedHorizon.MEDIUM_TERM


def _hypothesis_expiry(
    signals: tuple[CommercialSignal, ...],
    *,
    now: datetime,
    horizon: NeedHorizon,
) -> datetime:
    ttl_days = {
        NeedHorizon.IMMEDIATE: 30,
        NeedHorizon.NEAR_TERM: 90,
        NeedHorizon.MEDIUM_TERM: 180,
        NeedHorizon.LONG_TERM: 365,
    }[horizon]
    default_expiry = now + timedelta(days=ttl_days)
    source_expiries = [
        signal.expires_at
        for signal in signals
        if signal.expires_at is not None and signal.expires_at > now
    ]
    return min((default_expiry, *source_expiries))


def _source_contributions(
    signals: tuple[CommercialSignal, ...],
    *,
    now: datetime,
) -> tuple[SourceContribution, ...]:
    grouped: dict[str, list[CommercialSignal]] = defaultdict(list)
    for signal in signals:
        grouped[signal.corroboration_key].append(signal)
    return tuple(
        _contribution(key, tuple(grouped[key]), now=now) for key in sorted(grouped)
    )


def _contribution(
    independence_key: str,
    signals: tuple[CommercialSignal, ...],
    *,
    now: datetime,
) -> SourceContribution:
    support = max(
        (
            signal.confidence * _freshness(signal, now=now)
            for signal in signals
            if signal.polarity is SignalPolarity.SUPPORTING
        ),
        default=0.0,
    )
    contradiction = max(
        (
            signal.confidence
            for signal in signals
            if signal.polarity is SignalPolarity.CONTRADICTING
        ),
        default=0.0,
    )
    negative = max(
        (
            signal.confidence
            for signal in signals
            if signal.polarity is SignalPolarity.NEGATIVE
        ),
        default=0.0,
    )
    net = _clamp_signed(support - contradiction * 0.40 - negative * 0.30)
    if net >= 0:
        polarity = SignalPolarity.SUPPORTING
    elif contradiction >= negative:
        polarity = SignalPolarity.CONTRADICTING
    else:
        polarity = SignalPolarity.NEGATIVE
    return SourceContribution(
        independence_key=independence_key,
        polarity=polarity,
        signal_ids=tuple(signal.id for signal in signals),
        max_confidence=max(signal.confidence for signal in signals),
        contribution=round(net, 4),
    )


def _rationale(
    family: CyberServiceFamily,
    hypothesis_class: NeedHypothesisClass,
    evidence: _FusionEvidence,
    *,
    independent_support_count: int,
    confidence: float,
) -> str:
    explicit = sum(1 for signal in evidence.supporting if signal.is_explicit)
    return (
        f"{hypothesis_class.value} for {family.value}: "
        f"{len(evidence.supporting)} supporting signal(s) across "
        f"{independent_support_count} independent/corroboration group(s), "
        f"{explicit} explicit signal(s), {len(evidence.contradicting)} contradiction(s), "
        f"{len(evidence.negative)} negative signal(s); fused confidence={confidence:.2f}."
    )


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, value))


def _clamp_signed(value: float) -> float:
    return min(1.0, max(-1.0, value))

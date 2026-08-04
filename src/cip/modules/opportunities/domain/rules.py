from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import fmean
from uuid import UUID

from cip.modules.opportunities.domain.entities import (
    CommercialSignal,
    DataQuality,
    NeedHypothesis,
    Opportunity,
    OpportunityFamily,
    SignalType,
)
from cip.modules.opportunities.domain.scoring import (
    ComponentKind,
    OpportunityComponent,
    OpportunityScore,
)
from cip.shared.kernel.time import require_aware_utc

TENDER_TERMS = frozenset(
    {
        "siem",
        "soc",
        "security operations center",
        "managed detection and response",
        "mdr",
        "xdr",
        "log management",
        "security monitoring",
    }
)
JOB_TERMS = frozenset(
    {
        "soc analyst",
        "soc manager",
        "siem engineer",
        "security operations",
        "splunk",
        "microsoft sentinel",
        "sekoia",
        "xdr",
    }
)


@dataclass(frozen=True, slots=True)
class SiemSocRuleConfig:
    rule_id: str = "siem-soc-buying-intent"
    rule_version: str = "1.0.0"
    score_version: str = "1.0.0"
    config_version: str = "siem-soc-mvp-1"
    signal_window_days: int = 90
    opportunity_ttl_days: int = 30

    def __post_init__(self) -> None:
        if not self.rule_id.strip() or not self.rule_version.strip():
            raise ValueError("rule identity and version are required")
        if self.signal_window_days < 1 or self.opportunity_ttl_days < 1:
            raise ValueError("rule windows must be positive")


DEFAULT_SIEM_SOC_RULE_CONFIG = SiemSocRuleConfig()


@dataclass(frozen=True, slots=True)
class OpportunityEvaluation:
    hypothesis: NeedHypothesis
    opportunity: Opportunity


def evaluate_siem_soc_buying_intent(
    organization_id: UUID,
    signals: tuple[CommercialSignal, ...],
    *,
    now: datetime,
    config: SiemSocRuleConfig = DEFAULT_SIEM_SOC_RULE_CONFIG,
) -> OpportunityEvaluation | None:
    evaluated_at = require_aware_utc(now, field_name="now")
    eligible = tuple(
        signal
        for signal in signals
        if signal.organization_id == organization_id
        and signal.effective_at >= evaluated_at - timedelta(days=config.signal_window_days)
        and (signal.expires_at is None or signal.expires_at > evaluated_at)
        and _matches_signal(signal)
    )
    if not eligible:
        return None

    tender_signals = tuple(
        signal for signal in eligible if signal.signal_type is SignalType.PUBLIC_TENDER
    )
    job_signals = tuple(
        signal for signal in eligible if signal.signal_type is SignalType.JOB_POSTING
    )
    components = _score_components(
        tender_signals,
        job_signals,
        eligible,
        now=evaluated_at,
        config=config,
    )
    evidence_ids = tuple(dict.fromkeys(signal.evidence_id for signal in eligible))
    signal_ids = tuple(signal.id for signal in eligible)
    latest_evidence_at = max(signal.effective_at for signal in eligible)
    expires_at = evaluated_at + timedelta(days=config.opportunity_ttl_days)
    rationale = _build_rationale(tender_signals, job_signals)
    hypothesis = NeedHypothesis(
        organization_id=organization_id,
        family=OpportunityFamily.SIEM_SOC_BUYING_INTENT,
        rule_id=config.rule_id,
        rule_version=config.rule_version,
        rationale=rationale,
        signal_ids=signal_ids,
        evidence_ids=evidence_ids,
        generated_at=evaluated_at,
        expires_at=expires_at,
    )
    score = OpportunityScore(
        organization_id=organization_id,
        score_version=config.score_version,
        config_version=config.config_version,
        components=components,
        generated_at=evaluated_at,
        expires_at=expires_at,
    )
    confidence = round(fmean(signal.confidence for signal in eligible), 6)
    data_quality = (
        DataQuality.COMPLETE
        if tender_signals and job_signals and len(evidence_ids) >= 2
        else DataQuality.PARTIAL
    )
    opportunity = Opportunity(
        organization_id=organization_id,
        hypothesis_id=hypothesis.id,
        recommended_offer="SIEM / SOC discovery and architecture assessment",
        relevant_roles=("RSSI", "Responsable SOC", "DSI", "Achats IT"),
        trigger_summary=rationale,
        next_action=(
            "Review tender scope and procurement timeline"
            if tender_signals
            else "Validate hiring context and current SIEM / SOC operating model"
        ),
        score=score,
        confidence=confidence,
        last_evidence_at=latest_evidence_at,
        data_quality=data_quality,
    )
    return OpportunityEvaluation(hypothesis=hypothesis, opportunity=opportunity)


def _matches_signal(signal: CommercialSignal) -> bool:
    terms = TENDER_TERMS if signal.signal_type is SignalType.PUBLIC_TENDER else JOB_TERMS
    text = f"{signal.title} {signal.summary} {' '.join(signal.matched_terms)}".lower()
    return any(term in text for term in terms)


def _score_components(
    tenders: tuple[CommercialSignal, ...],
    jobs: tuple[CommercialSignal, ...],
    signals: tuple[CommercialSignal, ...],
    *,
    now: datetime,
    config: SiemSocRuleConfig,
) -> tuple[OpportunityComponent, ...]:
    evidence_ids = tuple(dict.fromkeys(signal.evidence_id for signal in signals))
    latest = max(signal.effective_at for signal in signals)
    age_days = max((now - latest).total_seconds() / 86_400, 0.0)
    freshness = max(0.0, 1.0 - age_days / config.signal_window_days)
    confidence = fmean(signal.confidence for signal in signals)
    return (
        OpportunityComponent(
            rule_id="public-tender-intent",
            value=1.0 if tenders else 0.0,
            weight=45.0,
            reason="A public procurement signal explicitly references SIEM or SOC capabilities.",
            evidence_ids=tuple(signal.evidence_id for signal in tenders),
        ),
        OpportunityComponent(
            rule_id="security-operations-hiring",
            value=min(len(jobs) / 3.0, 1.0),
            weight=25.0,
            reason="Recent public hiring indicates investment in security operations capability.",
            evidence_ids=tuple(signal.evidence_id for signal in jobs),
        ),
        OpportunityComponent(
            rule_id="cross-source-corroboration",
            value=1.0 if tenders and jobs else 0.0,
            weight=15.0,
            reason="Tender and hiring evidence independently corroborate the same need.",
            evidence_ids=evidence_ids,
        ),
        OpportunityComponent(
            rule_id="signal-freshness",
            value=round(freshness, 6),
            weight=10.0,
            reason="Recent evidence receives more weight than older observations.",
            evidence_ids=evidence_ids,
        ),
        OpportunityComponent(
            rule_id="evidence-confidence",
            value=round(confidence, 6),
            weight=5.0,
            reason="Provider evidence confidence contributes to the final priority.",
            evidence_ids=evidence_ids,
        ),
        OpportunityComponent(
            rule_id="single-source-penalty",
            value=0.25 if len(evidence_ids) == 1 else 0.0,
            weight=20.0,
            reason="A single evidence item requires additional analyst validation.",
            kind=ComponentKind.PENALTY,
            evidence_ids=evidence_ids,
        ),
    )


def _build_rationale(
    tenders: tuple[CommercialSignal, ...],
    jobs: tuple[CommercialSignal, ...],
) -> str:
    fragments: list[str] = []
    if tenders:
        fragments.append(f"{len(tenders)} public tender signal(s) mention SIEM/SOC needs")
    if jobs:
        fragments.append(f"{len(jobs)} security-operations job posting signal(s) were detected")
    return "; ".join(fragments) + "."

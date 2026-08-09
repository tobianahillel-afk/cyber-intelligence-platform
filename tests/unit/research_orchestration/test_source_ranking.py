from __future__ import annotations

from cip.modules.research_orchestration.domain import (
    ResearchRiskLevel,
    ResearchSourceCandidate,
    ResearchStepMode,
    rank_research_sources,
)


def test_ranking_filters_unsafe_or_non_executable_automated_sources() -> None:
    candidates = (
        _candidate("blocked-auth", authorized=False),
        _candidate("blocked-runtime", executable=False),
        _candidate("blocked-quota", quota_remaining=0),
        _candidate("blocked-risk", risk_level=ResearchRiskLevel.PROHIBITED),
        _candidate("safe-auto"),
    )

    ranked = rank_research_sources(candidates)

    assert [candidate.source_id for candidate in ranked] == ["safe-auto"]


def test_manual_link_can_rank_without_automation_authorization() -> None:
    manual = _candidate(
        "manual-search",
        mode=ResearchStepMode.MANUAL_LINK,
        authorized=False,
        executable=False,
        manual_link_allowed=True,
        value_score=0.8,
        freshness_score=0.8,
    )

    ranked = rank_research_sources((manual,))

    assert ranked == (manual,)


def test_ranking_prefers_value_freshness_low_cost_and_low_risk() -> None:
    strong = _candidate(
        "strong",
        value_score=0.9,
        freshness_score=0.9,
        estimated_cost=1.0,
        risk_level=ResearchRiskLevel.LOW,
    )
    weak = _candidate(
        "weak",
        value_score=0.5,
        freshness_score=0.5,
        estimated_cost=10.0,
        risk_level=ResearchRiskLevel.MEDIUM,
    )

    ranked = rank_research_sources((weak, strong))

    assert ranked == (strong, weak)


def _candidate(
    source_id: str,
    *,
    mode: ResearchStepMode = ResearchStepMode.AUTOMATED_ADAPTER,
    authorized: bool = True,
    executable: bool = True,
    manual_link_allowed: bool = False,
    freshness_score: float = 0.7,
    value_score: float = 0.7,
    estimated_cost: float = 1.0,
    quota_remaining: int | None = 100,
    risk_level: ResearchRiskLevel = ResearchRiskLevel.LOW,
) -> ResearchSourceCandidate:
    return ResearchSourceCandidate(
        source_id=source_id,
        tool_id=f"tool:{source_id}",
        mode=mode,
        authorized=authorized,
        executable=executable,
        manual_link_allowed=manual_link_allowed,
        freshness_score=freshness_score,
        value_score=value_score,
        estimated_cost=estimated_cost,
        quota_remaining=quota_remaining,
        risk_level=risk_level,
    )

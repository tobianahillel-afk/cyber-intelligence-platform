from __future__ import annotations

from cip.modules.research_orchestration.domain.enums import (
    ResearchRiskLevel,
    ResearchStepMode,
)
from cip.modules.research_orchestration.domain.models import ResearchSourceCandidate

_RISK_PENALTY = {
    ResearchRiskLevel.LOW: 0.0,
    ResearchRiskLevel.MEDIUM: 0.15,
    ResearchRiskLevel.HIGH: 0.4,
    ResearchRiskLevel.PROHIBITED: 1.0,
}


def rank_research_sources(
    candidates: tuple[ResearchSourceCandidate, ...],
) -> tuple[ResearchSourceCandidate, ...]:
    viable = tuple(candidate for candidate in candidates if _viable(candidate))
    return tuple(sorted(viable, key=_rank_key))


def _viable(candidate: ResearchSourceCandidate) -> bool:
    if candidate.risk_level is ResearchRiskLevel.PROHIBITED:
        return False
    if candidate.mode is ResearchStepMode.AUTOMATED_ADAPTER:
        return (
            candidate.authorized
            and candidate.executable
            and candidate.quota_remaining != 0
        )
    if candidate.mode is ResearchStepMode.MANUAL_LINK:
        return candidate.manual_link_allowed
    return True


def _rank_key(candidate: ResearchSourceCandidate) -> tuple[float, float, float, str, str]:
    cost_penalty = min(candidate.estimated_cost / 100.0, 1.0)
    score = (
        0.45 * candidate.value_score
        + 0.35 * candidate.freshness_score
        - 0.15 * cost_penalty
        - 0.25 * _RISK_PENALTY[candidate.risk_level]
    )
    mode_priority = 0.0 if candidate.mode is ResearchStepMode.PERSISTED_SEARCH else 0.1
    return (-score, mode_priority, candidate.estimated_cost, candidate.source_id, candidate.tool_id)

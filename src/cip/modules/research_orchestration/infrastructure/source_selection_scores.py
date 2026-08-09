from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.research_orchestration.domain import ResearchRiskLevel
from cip.modules.source_governance.domain.models import SourceStatus, SourceType
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.modules.source_portfolio.domain.models import FreshnessState
from cip.modules.source_portfolio.infrastructure.models import (
    SourceHealthRecord,
    SourcePortfolioRecord,
    SourceValueEventRecord,
)

_FRESHNESS_SCORES = {
    FreshnessState.FRESH.value: 1.0,
    FreshnessState.AGING.value: 0.75,
    FreshnessState.STALE_REFRESH_QUEUED.value: 0.4,
    FreshnessState.HISTORICAL_ONLY.value: 0.3,
    FreshnessState.SOURCE_UNAVAILABLE.value: 0.1,
    FreshnessState.AUTHORIZATION_EXPIRED.value: 0.0,
    FreshnessState.QUOTA_EXHAUSTED.value: 0.0,
    FreshnessState.COST_BUDGET_EXHAUSTED.value: 0.0,
}


def freshness_score(health: SourceHealthRecord | None) -> float:
    if health is None:
        return 0.0
    return _FRESHNESS_SCORES.get(health.freshness_state, 0.0)


def research_risk_level(
    source: SourceRecord,
    portfolio: SourcePortfolioRecord,
) -> ResearchRiskLevel:
    configured = portfolio.extra_metadata.get("research_risk_level")
    if isinstance(configured, str):
        try:
            return ResearchRiskLevel(configured)
        except ValueError:
            pass
    if source.status in {SourceStatus.BLOCKED.value, SourceStatus.QUARANTINED.value}:
        return ResearchRiskLevel.PROHIBITED
    if source.source_type == SourceType.BROWSER.value:
        return ResearchRiskLevel.PROHIBITED
    if source.source_type == SourceType.SEARCH_PROVIDER.value:
        return ResearchRiskLevel.MEDIUM
    return ResearchRiskLevel.LOW


def normalized_value_scores(session: Session) -> dict[str, float]:
    totals: dict[str, float] = {}
    for event in session.scalars(select(SourceValueEventRecord)).all():
        score = (
            event.commercial_projections * 5
            + event.identity_projections * 3
            + event.observations_written
            + (0 if event.not_modified else 1)
        )
        totals[event.source_id] = totals.get(event.source_id, 0.0) + float(score)
    maximum = max(totals.values(), default=0.0)
    if maximum <= 0:
        return {source_id: 0.0 for source_id in totals}
    return {source_id: value / maximum for source_id, value in totals.items()}

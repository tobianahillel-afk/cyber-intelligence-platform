from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.conditional_integrations.domain import ApprovalState, TermsReviewState
from cip.modules.conditional_integrations.infrastructure.models import (
    ConditionalProviderApprovalRecord,
    ConditionalProviderRuntimeControlRecord,
)
from cip.modules.provider_onboarding.domain.models import OnboardingState
from cip.modules.provider_onboarding.infrastructure.models import ProviderOnboardingRecord
from cip.modules.research_orchestration.domain import (
    ResearchRiskLevel,
    ResearchSourceCandidate,
    ResearchStepMode,
    rank_research_sources,
)
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.modules.source_portfolio.domain.models import CatalogStatus, FreshnessState
from cip.modules.source_portfolio.infrastructure.models import (
    AdapterCapabilityRecord,
    SourceHealthRecord,
    SourcePortfolioRecord,
    SourceValueEventRecord,
)
from cip.shared.kernel.time import require_aware_utc

_READY_ONBOARDING = {OnboardingState.CONNECTED.value, OnboardingState.NOT_REQUIRED.value}
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


def select_ranked_research_sources(
    session: Session,
    *,
    purpose: str,
    data_category: DataCategory,
    now: datetime,
) -> tuple[ResearchSourceCandidate, ...]:
    current = require_aware_utc(now, field_name="now")
    sources = tuple(session.scalars(select(SourceRecord).order_by(SourceRecord.id)))
    portfolios = {
        record.source_id: record
        for record in session.scalars(select(SourcePortfolioRecord)).all()
    }
    capabilities = {
        record.source_id: record
        for record in session.scalars(select(AdapterCapabilityRecord)).all()
    }
    health = {
        record.source_id: record
        for record in session.scalars(select(SourceHealthRecord)).all()
    }
    values = _normalized_value_scores(session)
    candidates = [_persisted_candidate()]
    for source in sources:
        portfolio = portfolios.get(source.id)
        capability = capabilities.get(source.id)
        source_health = health.get(source.id)
        if portfolio is not None and capability is not None:
            candidates.append(
                _automated_candidate(
                    session,
                    source,
                    portfolio,
                    capability,
                    source_health,
                    value_score=values.get(source.id, 0.0),
                    purpose=purpose,
                    data_category=data_category,
                    now=current,
                )
            )
        manual = _manual_candidate(
            source,
            value_score=values.get(source.id, 0.0),
            data_category=data_category,
        )
        if manual is not None:
            candidates.append(manual)
    return rank_research_sources(candidates)


def _persisted_candidate() -> ResearchSourceCandidate:
    return ResearchSourceCandidate(
        source_id="persisted-evidence",
        tool_id="public-footprint-search",
        mode=ResearchStepMode.PERSISTED_SEARCH,
        authorized=False,
        executable=False,
        manual_link_allowed=False,
        freshness_score=1.0,
        value_score=1.0,
        estimated_cost=0.0,
        quota_remaining=None,
        risk_level=ResearchRiskLevel.LOW,
    )


def _automated_candidate(
    session: Session,
    source: SourceRecord,
    portfolio: SourcePortfolioRecord,
    capability: AdapterCapabilityRecord,
    health: SourceHealthRecord | None,
    *,
    value_score: float,
    purpose: str,
    data_category: DataCategory,
    now: datetime,
) -> ResearchSourceCandidate:
    authorized = _automated_authorized(
        session,
        source,
        portfolio,
        purpose=purpose,
        data_category=data_category,
        now=now,
    )
    executable = _portfolio_executable(portfolio, capability, health, now=now)
    return ResearchSourceCandidate(
        source_id=source.id,
        tool_id=capability.adapter_id,
        mode=ResearchStepMode.AUTOMATED_ADAPTER,
        authorized=authorized,
        executable=executable,
        manual_link_allowed=False,
        freshness_score=_freshness_score(health),
        value_score=value_score,
        estimated_cost=capability.cost_per_request,
        quota_remaining=health.quota_remaining if health is not None else None,
        risk_level=_risk_level(source, portfolio),
    )


def _manual_candidate(
    source: SourceRecord,
    *,
    value_score: float,
    data_category: DataCategory,
) -> ResearchSourceCandidate | None:
    category = data_category.value
    allowed = (
        source.source_type == SourceType.SEARCH_PROVIDER.value
        and source.status in {SourceStatus.ENABLED.value, SourceStatus.CONDITIONAL.value}
        and category in source.allowed_data_categories
        and category not in source.prohibited_data_categories
    )
    if not allowed:
        return None
    return ResearchSourceCandidate(
        source_id=source.id,
        tool_id=f"manual:{source.id}",
        mode=ResearchStepMode.MANUAL_LINK,
        authorized=False,
        executable=False,
        manual_link_allowed=True,
        freshness_score=0.5,
        value_score=value_score,
        estimated_cost=0.0,
        quota_remaining=None,
        risk_level=ResearchRiskLevel.MEDIUM,
    )


def _automated_authorized(
    session: Session,
    source: SourceRecord,
    portfolio: SourcePortfolioRecord,
    *,
    purpose: str,
    data_category: DataCategory,
    now: datetime,
) -> bool:
    if source.status != SourceStatus.ENABLED.value:
        return False
    if source.authorization_status != AuthorizationStatus.APPROVED.value:
        return False
    if data_category.value not in source.allowed_data_categories:
        return False
    if data_category.value in source.prohibited_data_categories:
        return False
    if purpose not in source.approved_purposes or not source.automated_collection_allowed:
        return False
    expires_at = _aware(source.authorization_expires_at)
    if expires_at is not None and expires_at <= now:
        return False
    if not _onboarding_ready(session, source.id):
        return False
    return _conditional_approval_ready(session, source.id, portfolio, purpose, data_category, now)


def _onboarding_ready(session: Session, source_id: str) -> bool:
    record = session.get(ProviderOnboardingRecord, source_id)
    return record is None or record.state in _READY_ONBOARDING


def _conditional_approval_ready(
    session: Session,
    source_id: str,
    portfolio: SourcePortfolioRecord,
    purpose: str,
    data_category: DataCategory,
    now: datetime,
) -> bool:
    approval = session.scalar(
        select(ConditionalProviderApprovalRecord).where(
            ConditionalProviderApprovalRecord.source_id == source_id
        )
    )
    if approval is None:
        return True
    if approval.state != ApprovalState.APPROVED.value:
        return False
    if approval.terms_state != TermsReviewState.CURRENT.value or approval.revoked_at is not None:
        return False
    if purpose not in approval.approved_purposes:
        return False
    if data_category.value not in approval.approved_data_categories:
        return False
    if not approval.automated_collection_allowed:
        return False
    review_due = _aware(approval.review_due_at)
    expires_at = _aware(approval.expires_at)
    if (review_due is not None and review_due <= now) or (
        expires_at is not None and expires_at <= now
    ):
        return False
    access_method = portfolio.extra_metadata.get("conditional_access_method")
    if not isinstance(access_method, str) or access_method != approval.access_method:
        return False
    control = session.scalar(
        select(ConditionalProviderRuntimeControlRecord).where(
            ConditionalProviderRuntimeControlRecord.source_id == source_id
        )
    )
    return control is None or (not control.paused and not control.kill_switch_active)


def _portfolio_executable(
    portfolio: SourcePortfolioRecord,
    capability: AdapterCapabilityRecord,
    health: SourceHealthRecord | None,
    *,
    now: datetime,
) -> bool:
    if portfolio.status != CatalogStatus.EXECUTABLE.value or health is None:
        return False
    expires_at = _aware(portfolio.authorization_expires_at)
    if expires_at is not None and expires_at <= now:
        return False
    if health.quota_remaining == 0:
        return False
    if (
        capability.cost_per_request > 0
        and portfolio.monthly_cost_limit is not None
        and health.monthly_cost_used + capability.cost_per_request > portfolio.monthly_cost_limit
    ):
        return False
    return health.freshness_state not in {
        FreshnessState.AUTHORIZATION_EXPIRED.value,
        FreshnessState.QUOTA_EXHAUSTED.value,
        FreshnessState.COST_BUDGET_EXHAUSTED.value,
    }


def _freshness_score(health: SourceHealthRecord | None) -> float:
    if health is None:
        return 0.0
    return _FRESHNESS_SCORES.get(health.freshness_state, 0.0)


def _risk_level(
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


def _normalized_value_scores(session: Session) -> dict[str, float]:
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


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

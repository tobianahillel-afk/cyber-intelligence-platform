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
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    SourceStatus,
)
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.modules.source_portfolio.domain.models import CatalogStatus, FreshnessState
from cip.modules.source_portfolio.infrastructure.models import (
    AdapterCapabilityRecord,
    SourceHealthRecord,
    SourcePortfolioRecord,
)

_READY_ONBOARDING = {OnboardingState.CONNECTED.value, OnboardingState.NOT_REQUIRED.value}


def automated_source_authorized(
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
    expires_at = persistence_utc(source.authorization_expires_at)
    if expires_at is not None and expires_at <= now:
        return False
    if not _onboarding_ready(session, source.id):
        return False
    return _conditional_approval_ready(
        session,
        source.id,
        portfolio,
        purpose,
        data_category,
        now,
    )


def source_portfolio_executable(
    portfolio: SourcePortfolioRecord,
    capability: AdapterCapabilityRecord,
    health: SourceHealthRecord | None,
    *,
    now: datetime,
) -> bool:
    if portfolio.status != CatalogStatus.EXECUTABLE.value or health is None:
        return False
    expires_at = persistence_utc(portfolio.authorization_expires_at)
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


def persistence_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


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
    review_due = persistence_utc(approval.review_due_at)
    expires_at = persistence_utc(approval.expires_at)
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

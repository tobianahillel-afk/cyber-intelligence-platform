from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.conditional_integrations.domain import (
    ConditionalAccessMethod,
    ConditionalExecutionRequest,
    ConditionalRuntimeDependencies,
)
from cip.modules.provider_onboarding.domain.models import OnboardingState
from cip.modules.provider_onboarding.infrastructure.models import ProviderOnboardingRecord
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    CollectionRequest,
    DataCategory,
    SourceAuthorization,
    SourcePolicy,
    SourceRuntimeState,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.modules.source_portfolio.application.execution import source_execution_allowed
from cip.modules.source_portfolio.infrastructure.models import (
    AdapterCapabilityRecord,
    SourceHealthRecord,
    SourcePortfolioRecord,
)
from cip.shared.kernel.time import require_aware_utc

_NON_CONNECTED_METHODS = {
    ConditionalAccessMethod.AUTHORIZED_EXPORT,
    ConditionalAccessMethod.MANUAL_IMPORT,
}


def resolve_runtime_dependencies(
    session: Session,
    request: ConditionalExecutionRequest,
    *,
    now: datetime,
) -> ConditionalRuntimeDependencies:
    current = require_aware_utc(now, field_name="now")
    source_id = request.source_id
    source = session.get(SourceRecord, source_id)
    portfolio = session.get(SourcePortfolioRecord, source_id)
    health = session.get(SourceHealthRecord, source_id)
    return ConditionalRuntimeDependencies(
        onboarding_state=_onboarding_state(session, request),
        source_policy_allowed=_source_policy_allowed(
            source,
            health,
            request,
            now=current,
        ),
        source_portfolio_allowed=_portfolio_allowed(
            session,
            portfolio,
            health,
            source_id=source_id,
            now=current,
        ),
        adapter_capability_present=_capability_present(session, source_id),
        quota_remaining=health.quota_remaining if health is not None else None,
        monthly_cost_used=health.monthly_cost_used if health is not None else 0.0,
        monthly_cost_limit=(
            portfolio.monthly_cost_limit if portfolio is not None else None
        ),
    )


def _onboarding_state(
    session: Session,
    request: ConditionalExecutionRequest,
) -> OnboardingState:
    record = session.get(ProviderOnboardingRecord, request.source_id)
    if record is None:
        if request.access_method in _NON_CONNECTED_METHODS:
            return OnboardingState.NOT_REQUIRED
        return OnboardingState.NOT_CONFIGURED
    try:
        return OnboardingState(record.state)
    except ValueError:
        return OnboardingState.NOT_CONFIGURED


def _source_policy_allowed(
    record: SourceRecord | None,
    health: SourceHealthRecord | None,
    request: ConditionalExecutionRequest,
    *,
    now: datetime,
) -> bool:
    if record is None:
        return False
    try:
        policy = _policy(record)
        authorization = _authorization(record)
    except ValueError:
        return False
    decision = policy.evaluate(
        CollectionRequest(
            data_category=request.data_category,
            target_url=request.target_url,
            purpose=request.purpose,
            automated=request.automated,
            store_raw_content=request.store_raw_content,
            human_review_completed=False,
        ),
        authorization,
        SourceRuntimeState(
            remaining_requests=health.quota_remaining if health is not None else None,
            last_success_at=_aware(health.last_success_at) if health is not None else None,
        ),
        now=now,
    )
    return decision.allowed


def _policy(record: SourceRecord) -> SourcePolicy:
    return SourcePolicy(
        id=record.id,
        name=record.name,
        base_url=record.base_url,
        status=SourceStatus(record.status),
        source_type=SourceType(record.source_type),
        owner=record.owner,
        allowed_data_categories=frozenset(
            DataCategory(value) for value in record.allowed_data_categories
        ),
        prohibited_data_categories=frozenset(
            DataCategory(value) for value in record.prohibited_data_categories
        ),
        terms_url=record.terms_url,
        licence=record.licence,
        rate_limit_per_minute=record.rate_limit_per_minute,
        retention_days=record.retention_days,
        attribution_required=record.attribution_required,
        raw_content_storage=record.raw_content_storage,
        human_review_required=record.human_review_required,
    )


def _authorization(record: SourceRecord) -> SourceAuthorization:
    return SourceAuthorization(
        status=AuthorizationStatus(record.authorization_status),
        document_reference=record.authorization_document_reference,
        reviewed_at=_aware(record.authorization_reviewed_at),
        expires_at=_aware(record.authorization_expires_at),
        approved_hosts=frozenset(record.approved_hosts),
        approved_path_prefixes=tuple(record.approved_path_prefixes),
        approved_purposes=frozenset(record.approved_purposes),
        automated_collection_allowed=record.automated_collection_allowed,
        raw_storage_allowed=record.raw_storage_allowed,
    )


def _portfolio_allowed(
    session: Session,
    portfolio: SourcePortfolioRecord | None,
    health: SourceHealthRecord | None,
    *,
    source_id: str,
    now: datetime,
) -> bool:
    if portfolio is None or health is None:
        return False
    return source_execution_allowed(session, source_id, now=now)


def _capability_present(session: Session, source_id: str) -> bool:
    return (
        session.scalar(
            select(AdapterCapabilityRecord.source_id)
            .where(AdapterCapabilityRecord.source_id == source_id)
            .limit(1)
        )
        is not None
    )


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

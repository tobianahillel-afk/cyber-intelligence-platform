from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.conditional_integrations.domain import ApprovalState
from cip.modules.conditional_integrations.infrastructure.models import (
    ConditionalProviderApprovalRecord,
    ConditionalProviderRuntimeControlRecord,
)
from cip.modules.provider_onboarding.domain.models import OnboardingState
from cip.modules.provider_onboarding.infrastructure.models import ProviderOnboardingRecord
from cip.modules.research_orchestration.domain import (
    ResearchPlan,
    ResearchRuntimeState,
    ResearchStep,
    ResearchStepMode,
)
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
from cip.modules.source_portfolio.domain.models import CatalogStatus
from cip.modules.source_portfolio.infrastructure.models import (
    AdapterCapabilityRecord,
    SourceHealthRecord,
    SourcePortfolioRecord,
)
from cip.shared.kernel.time import require_aware_utc

_READY_ONBOARDING = {OnboardingState.CONNECTED.value, OnboardingState.NOT_REQUIRED.value}
_MANUAL_SOURCE_STATES = {SourceStatus.ENABLED.value, SourceStatus.CONDITIONAL.value}


def resolve_research_runtime(
    session: Session,
    plan: ResearchPlan,
    step: ResearchStep,
    *,
    now: datetime,
) -> ResearchRuntimeState:
    current = require_aware_utc(now, field_name="now")
    if step.mode is ResearchStepMode.PERSISTED_SEARCH:
        return ResearchRuntimeState()
    if step.mode is ResearchStepMode.MANUAL_LINK:
        return ResearchRuntimeState(
            manual_link_allowed=_manual_link_allowed(session, plan, step)
        )
    if step.mode is ResearchStepMode.APPROVED_INGESTION:
        return ResearchRuntimeState(ingestion_path_approved=False)
    return _automated_runtime(session, plan, step, now=current)


def _automated_runtime(
    session: Session,
    plan: ResearchPlan,
    step: ResearchStep,
    *,
    now: datetime,
) -> ResearchRuntimeState:
    source = session.get(SourceRecord, step.source_id)
    portfolio = session.get(SourcePortfolioRecord, step.source_id)
    health = session.get(SourceHealthRecord, step.source_id)
    authorized = _source_policy_allowed(source, health, plan, step, now=now)
    authorized = authorized and _onboarding_ready(session, step.source_id)
    authorized = authorized and _conditional_controls_allow(
        session,
        step.source_id,
        now=now,
    )
    return ResearchRuntimeState(
        source_authorized=authorized,
        source_executable=_source_executable(
            session,
            portfolio,
            health,
            source_id=step.source_id,
            now=now,
        ),
        adapter_capability_present=_exact_capability_present(session, step),
        quota_remaining=health.quota_remaining if health is not None else None,
    )


def _source_policy_allowed(
    source: SourceRecord | None,
    health: SourceHealthRecord | None,
    plan: ResearchPlan,
    step: ResearchStep,
    *,
    now: datetime,
) -> bool:
    if source is None or step.target_url is None:
        return False
    try:
        policy = _policy(source)
        authorization = _authorization(source)
    except ValueError:
        return False
    decision = policy.evaluate(
        CollectionRequest(
            data_category=step.data_category,
            target_url=step.target_url,
            purpose=step.purpose,
            automated=True,
            store_raw_content=False,
            human_review_completed=step.step_key in plan.approved_step_keys,
        ),
        authorization,
        SourceRuntimeState(
            remaining_requests=health.quota_remaining if health is not None else None,
            last_success_at=_aware(health.last_success_at) if health is not None else None,
        ),
        now=now,
    )
    return decision.allowed


def _manual_link_allowed(
    session: Session,
    plan: ResearchPlan,
    step: ResearchStep,
) -> bool:
    source = session.get(SourceRecord, step.source_id)
    if source is None or step.target_url is None:
        return False
    if source.source_type != SourceType.SEARCH_PROVIDER.value:
        return False
    if source.status not in _MANUAL_SOURCE_STATES:
        return False
    category = step.data_category.value
    if (
        category not in source.allowed_data_categories
        or category in source.prohibited_data_categories
    ):
        return False
    target = urlparse(step.target_url)
    base = urlparse(source.base_url)
    return (
        target.scheme == "https"
        and target.hostname == base.hostname
        and step.step_key in plan.approved_step_keys
    )


def _source_executable(
    session: Session,
    portfolio: SourcePortfolioRecord | None,
    health: SourceHealthRecord | None,
    *,
    source_id: str,
    now: datetime,
) -> bool:
    if portfolio is None or health is None:
        return False
    if portfolio.status != CatalogStatus.EXECUTABLE.value:
        return False
    return source_execution_allowed(session, source_id, now=now)


def _exact_capability_present(session: Session, step: ResearchStep) -> bool:
    return session.get(AdapterCapabilityRecord, (step.source_id, step.tool_id)) is not None


def _onboarding_ready(session: Session, source_id: str) -> bool:
    record = session.get(ProviderOnboardingRecord, source_id)
    return record is None or record.state in _READY_ONBOARDING


def _conditional_controls_allow(
    session: Session,
    source_id: str,
    *,
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
    expires_at = _aware(approval.expires_at)
    if expires_at is not None and expires_at <= now:
        return False
    control = session.scalar(
        select(ConditionalProviderRuntimeControlRecord).where(
            ConditionalProviderRuntimeControlRecord.source_id == source_id
        )
    )
    return control is None or (not control.paused and not control.kill_switch_active)


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


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

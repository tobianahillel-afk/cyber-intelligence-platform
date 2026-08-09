from __future__ import annotations

from datetime import datetime

from cip.modules.conditional_integrations.domain.enums import (
    ApprovalState,
    ConditionalAccessMethod,
    ConditionalBlockReason,
    ConditionalProviderKind,
    TermsReviewState,
)
from cip.modules.conditional_integrations.domain.models import (
    ConditionalExecutionDecision,
    ConditionalExecutionRequest,
    ConditionalRuntimeDependencies,
    ProviderApprovalDossier,
)
from cip.modules.provider_onboarding.domain.models import OnboardingState
from cip.shared.kernel.time import require_aware_utc

_PROVIDER_METHODS: dict[ConditionalProviderKind, frozenset[ConditionalAccessMethod]] = {
    ConditionalProviderKind.LINKEDIN: frozenset(
        {
            ConditionalAccessMethod.OFFICIAL_API,
            ConditionalAccessMethod.LICENSED_API,
        }
    ),
    ConditionalProviderKind.DISCORD: frozenset(
        {
            ConditionalAccessMethod.ADMIN_INSTALLED_CONNECTOR,
            ConditionalAccessMethod.AUTHORIZED_EXPORT,
        }
    ),
    ConditionalProviderKind.BRIXHUB: frozenset(),
    ConditionalProviderKind.PREMIUM_CTI: frozenset(
        {
            ConditionalAccessMethod.LICENSED_API,
            ConditionalAccessMethod.AUTHORIZED_EXPORT,
        }
    ),
    ConditionalProviderKind.COMMERCIAL_DATA: frozenset(
        {
            ConditionalAccessMethod.LICENSED_API,
            ConditionalAccessMethod.AUTHORIZED_EXPORT,
            ConditionalAccessMethod.CUSTOMER_PROVIDED_ACCESS,
        }
    ),
    ConditionalProviderKind.OTHER: frozenset(
        {
            ConditionalAccessMethod.OFFICIAL_API,
            ConditionalAccessMethod.LICENSED_API,
            ConditionalAccessMethod.ADMIN_INSTALLED_CONNECTOR,
            ConditionalAccessMethod.AUTHORIZED_EXPORT,
            ConditionalAccessMethod.CUSTOMER_PROVIDED_ACCESS,
            ConditionalAccessMethod.MANUAL_IMPORT,
        }
    ),
}

_NON_CONNECTED_METHODS = {
    ConditionalAccessMethod.AUTHORIZED_EXPORT,
    ConditionalAccessMethod.MANUAL_IMPORT,
}


def evaluate_conditional_execution(
    dossier: ProviderApprovalDossier,
    request: ConditionalExecutionRequest,
    dependencies: ConditionalRuntimeDependencies,
    *,
    now: datetime,
) -> ConditionalExecutionDecision:
    current = require_aware_utc(now, field_name="now")
    reasons: list[ConditionalBlockReason] = []
    _append_state_reasons(reasons, dossier, current)
    if request.source_id != dossier.source_id:
        reasons.append(ConditionalBlockReason.SOURCE_MISMATCH)
    if request.access_method != dossier.access_method:
        reasons.append(ConditionalBlockReason.ACCESS_METHOD_NOT_APPROVED)
    if request.access_method not in _PROVIDER_METHODS[dossier.provider_kind]:
        reasons.append(ConditionalBlockReason.PROVIDER_METHOD_NOT_PERMITTED)
    if not request.requested_scopes.issubset(dossier.approved_scopes):
        reasons.append(ConditionalBlockReason.SCOPE_NOT_APPROVED)
    if not request.requested_fields.issubset(dossier.approved_fields):
        reasons.append(ConditionalBlockReason.FIELD_NOT_APPROVED)
    if request.purpose not in dossier.approved_purposes:
        reasons.append(ConditionalBlockReason.PURPOSE_NOT_APPROVED)
    if request.data_category not in dossier.approved_data_categories:
        reasons.append(ConditionalBlockReason.CATEGORY_NOT_APPROVED)
    if dossier.retention_days is None or request.retention_days > dossier.retention_days:
        reasons.append(ConditionalBlockReason.RETENTION_EXCEEDS_APPROVAL)
    if request.automated and not dossier.automated_collection_allowed:
        reasons.append(ConditionalBlockReason.AUTOMATION_NOT_APPROVED)
    if dossier.account_reference and request.account_reference != dossier.account_reference:
        reasons.append(ConditionalBlockReason.ACCOUNT_MISMATCH)
    _append_runtime_reasons(reasons, request, dependencies)
    unique_reasons = tuple(dict.fromkeys(reasons))
    if unique_reasons:
        return ConditionalExecutionDecision(False, unique_reasons)
    return ConditionalExecutionDecision(True, (ConditionalBlockReason.ALLOWED,))


def provider_method_is_permitted(
    provider_kind: ConditionalProviderKind,
    access_method: ConditionalAccessMethod,
) -> bool:
    return access_method in _PROVIDER_METHODS[provider_kind]


def _append_state_reasons(
    reasons: list[ConditionalBlockReason],
    dossier: ProviderApprovalDossier,
    now: datetime,
) -> None:
    state_reason = {
        ApprovalState.DRAFT: ConditionalBlockReason.DOSSIER_NOT_APPROVED,
        ApprovalState.PENDING_REVIEW: ConditionalBlockReason.DOSSIER_NOT_APPROVED,
        ApprovalState.EXPIRED: ConditionalBlockReason.DOSSIER_EXPIRED,
        ApprovalState.REVOKED: ConditionalBlockReason.DOSSIER_REVOKED,
        ApprovalState.PAUSED: ConditionalBlockReason.DOSSIER_PAUSED,
    }.get(dossier.state)
    if state_reason is not None:
        reasons.append(state_reason)
    if dossier.expires_at is not None and dossier.expires_at <= now:
        reasons.append(ConditionalBlockReason.DOSSIER_EXPIRED)
    if dossier.review_due_at is not None and dossier.review_due_at <= now:
        reasons.append(ConditionalBlockReason.TERMS_REVIEW_REQUIRED)
    if dossier.terms_state is not TermsReviewState.CURRENT:
        reasons.append(ConditionalBlockReason.TERMS_REVIEW_REQUIRED)


def _append_runtime_reasons(
    reasons: list[ConditionalBlockReason],
    request: ConditionalExecutionRequest,
    dependencies: ConditionalRuntimeDependencies,
) -> None:
    ready_states = {OnboardingState.CONNECTED}
    if request.access_method in _NON_CONNECTED_METHODS:
        ready_states.add(OnboardingState.NOT_REQUIRED)
    if dependencies.onboarding_state not in ready_states:
        reasons.append(ConditionalBlockReason.ONBOARDING_NOT_READY)
    if not dependencies.source_policy_allowed:
        reasons.append(ConditionalBlockReason.SOURCE_POLICY_DENIED)
    if not dependencies.adapter_capability_present:
        reasons.append(ConditionalBlockReason.CAPABILITY_MISSING)
    if dependencies.kill_switch_active:
        reasons.append(ConditionalBlockReason.KILL_SWITCH_ACTIVE)
    if dependencies.quota_remaining == 0:
        reasons.append(ConditionalBlockReason.QUOTA_EXHAUSTED)
    if (
        dependencies.monthly_cost_limit is not None
        and dependencies.monthly_cost_used >= dependencies.monthly_cost_limit
    ):
        reasons.append(ConditionalBlockReason.COST_BUDGET_EXHAUSTED)

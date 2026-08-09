from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.conditional_integrations.domain import (
    ConditionalBlockReason,
    ConditionalExecutionDecision,
    ConditionalExecutionRequest,
    ConditionalRuntimeDependencies,
    evaluate_conditional_execution,
)
from cip.modules.conditional_integrations.infrastructure.control_persistence import (
    get_or_create_runtime_control,
)
from cip.modules.conditional_integrations.infrastructure.hydration import (
    dossier_from_record,
)
from cip.modules.conditional_integrations.infrastructure.models import (
    ConditionalExecutionDecisionRecord,
    ConditionalProviderApprovalRecord,
)
from cip.modules.conditional_integrations.infrastructure.payloads import (
    execution_decision_key,
)
from cip.shared.kernel.time import require_aware_utc


def evaluate_and_audit_conditional_execution(
    session: Session,
    request: ConditionalExecutionRequest,
    dependencies: ConditionalRuntimeDependencies,
    *,
    now: datetime,
) -> ConditionalExecutionDecision:
    evaluated_at = require_aware_utc(now, field_name="now")
    approval = _approval(session, request.source_id)
    dossier = dossier_from_record(approval)
    control = get_or_create_runtime_control(session, request.source_id, now=evaluated_at)
    effective_dependencies = replace(
        dependencies,
        provider_paused=dependencies.provider_paused or control.paused,
        kill_switch_active=dependencies.kill_switch_active or control.kill_switch_active,
    )
    decision = evaluate_conditional_execution(
        dossier,
        request,
        effective_dependencies,
        now=evaluated_at,
    )
    decision = _apply_provider_pause(decision, effective_dependencies.provider_paused)
    _persist_execution_decision(
        session,
        approval=approval,
        request=request,
        dependencies=effective_dependencies,
        decision=decision,
        evaluated_at=evaluated_at,
    )
    session.flush()
    return decision


def _apply_provider_pause(
    decision: ConditionalExecutionDecision,
    provider_paused: bool,
) -> ConditionalExecutionDecision:
    if not provider_paused:
        return decision
    reasons = tuple(
        reason for reason in decision.reasons if reason is not ConditionalBlockReason.ALLOWED
    )
    reasons = (*reasons, ConditionalBlockReason.PROVIDER_PAUSED)
    return ConditionalExecutionDecision(False, tuple(dict.fromkeys(reasons)))


def _persist_execution_decision(
    session: Session,
    *,
    approval: ConditionalProviderApprovalRecord,
    request: ConditionalExecutionRequest,
    dependencies: ConditionalRuntimeDependencies,
    decision: ConditionalExecutionDecision,
    evaluated_at: datetime,
) -> None:
    key = execution_decision_key(
        request,
        dependencies,
        decision,
        evaluated_at=evaluated_at.isoformat(),
    )
    if session.scalar(
        select(ConditionalExecutionDecisionRecord.id).where(
            ConditionalExecutionDecisionRecord.decision_key == key
        )
    ):
        return
    session.add(
        ConditionalExecutionDecisionRecord(
            id=uuid4(),
            approval_id=approval.id,
            decision_key=key,
            source_id=request.source_id,
            access_method=request.access_method.value,
            purpose=request.purpose,
            data_category=request.data_category.value,
            target_url=request.target_url,
            requested_scopes=sorted(request.requested_scopes),
            requested_fields=sorted(request.requested_fields),
            retention_days=request.retention_days,
            automated=request.automated,
            store_raw_content=request.store_raw_content,
            account_reference=request.account_reference,
            onboarding_state=dependencies.onboarding_state.value,
            source_policy_allowed=dependencies.source_policy_allowed,
            source_portfolio_allowed=dependencies.source_portfolio_allowed,
            adapter_capability_present=dependencies.adapter_capability_present,
            provider_paused=dependencies.provider_paused,
            kill_switch_active=dependencies.kill_switch_active,
            quota_remaining=dependencies.quota_remaining,
            monthly_cost_used=dependencies.monthly_cost_used,
            monthly_cost_limit=dependencies.monthly_cost_limit,
            allowed=decision.allowed,
            reasons=[reason.value for reason in decision.reasons],
            evaluated_at=evaluated_at,
            created_at=evaluated_at,
        )
    )


def _approval(session: Session, source_id: str) -> ConditionalProviderApprovalRecord:
    record = session.scalar(
        select(ConditionalProviderApprovalRecord).where(
            ConditionalProviderApprovalRecord.source_id == source_id
        )
    )
    if record is None:
        raise LookupError(f"conditional provider approval not found: {source_id}")
    return record

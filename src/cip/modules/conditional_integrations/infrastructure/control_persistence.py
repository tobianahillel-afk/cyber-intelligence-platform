from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.conditional_integrations.domain import (
    ProviderControlDecision,
    ProviderRuntimeControl,
    apply_control_decision,
)
from cip.modules.conditional_integrations.infrastructure.hydration import control_from_record
from cip.modules.conditional_integrations.infrastructure.models import (
    ConditionalProviderApprovalRecord,
    ConditionalProviderControlDecisionRecord,
    ConditionalProviderRuntimeControlRecord,
)
from cip.modules.conditional_integrations.infrastructure.payloads import control_decision_key
from cip.shared.kernel.time import require_aware_utc


def apply_persisted_control_decision(
    session: Session,
    decision: ProviderControlDecision,
    *,
    now: datetime,
) -> ConditionalProviderRuntimeControlRecord:
    current_time = require_aware_utc(now, field_name="now")
    if decision.decided_at > current_time:
        raise ValueError("control decision cannot be in the future")
    approval = _approval(session, decision.source_id)
    control = _control(session, approval, decision, current_time)
    current = control_from_record(control)
    resulting = apply_control_decision(current, decision)
    decision_key = control_decision_key(decision, resulting)
    if _decision_exists(session, decision_key):
        return control
    session.add(
        ConditionalProviderControlDecisionRecord(
            id=uuid4(),
            control_id=control.id,
            decision_key=decision_key,
            source_id=decision.source_id,
            action=decision.action.value,
            actor=decision.actor,
            reason=decision.reason,
            resulting_paused=resulting.paused,
            resulting_kill_switch_active=resulting.kill_switch_active,
            decided_at=decision.decided_at,
            created_at=current_time,
        )
    )
    control.paused = resulting.paused
    control.kill_switch_active = resulting.kill_switch_active
    control.paused_reason = resulting.paused_reason
    control.updated_at = resulting.updated_at
    session.flush()
    return control


def get_or_create_runtime_control(
    session: Session,
    source_id: str,
    *,
    now: datetime,
) -> ConditionalProviderRuntimeControlRecord:
    current_time = require_aware_utc(now, field_name="now")
    approval = _approval(session, source_id)
    existing = session.scalar(
        select(ConditionalProviderRuntimeControlRecord).where(
            ConditionalProviderRuntimeControlRecord.approval_id == approval.id
        )
    )
    if existing is not None:
        return existing
    record = ConditionalProviderRuntimeControlRecord(
        id=uuid4(),
        approval_id=approval.id,
        source_id=source_id,
        paused=False,
        kill_switch_active=False,
        paused_reason=None,
        updated_at=current_time,
    )
    session.add(record)
    session.flush()
    return record


def _approval(session: Session, source_id: str) -> ConditionalProviderApprovalRecord:
    record = session.scalar(
        select(ConditionalProviderApprovalRecord).where(
            ConditionalProviderApprovalRecord.source_id == source_id
        )
    )
    if record is None:
        raise LookupError(f"conditional provider approval not found: {source_id}")
    return record


def _control(
    session: Session,
    approval: ConditionalProviderApprovalRecord,
    decision: ProviderControlDecision,
    now: datetime,
) -> ConditionalProviderRuntimeControlRecord:
    existing = session.scalar(
        select(ConditionalProviderRuntimeControlRecord).where(
            ConditionalProviderRuntimeControlRecord.approval_id == approval.id
        )
    )
    if existing is not None:
        return existing
    initial_time = min(now, decision.decided_at)
    record = ConditionalProviderRuntimeControlRecord(
        id=uuid4(),
        approval_id=approval.id,
        source_id=approval.source_id,
        paused=False,
        kill_switch_active=False,
        paused_reason=None,
        updated_at=initial_time,
    )
    session.add(record)
    session.flush()
    return record


def _decision_exists(session: Session, decision_key: str) -> bool:
    return (
        session.scalar(
            select(ConditionalProviderControlDecisionRecord.id).where(
                ConditionalProviderControlDecisionRecord.decision_key == decision_key
            )
        )
        is not None
    )

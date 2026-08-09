from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.research_orchestration.domain import ResearchStepMode, ResearchStepState
from cip.modules.research_orchestration.infrastructure.models import (
    ResearchStepAttemptRecord,
    ResearchStepRecord,
)
from cip.modules.research_orchestration.infrastructure.payloads import attempt_key
from cip.shared.kernel.time import require_aware_utc

_ATTEMPTABLE_STATES = {
    ResearchStepState.READY.value,
    ResearchStepState.MANUAL_ACTION_REQUIRED.value,
}


def begin_research_attempt(
    session: Session,
    plan_id: UUID,
    step_key: str,
    *,
    actor: str,
    idempotency_key: str,
    now: datetime,
) -> ResearchStepAttemptRecord:
    current = require_aware_utc(now, field_name="now")
    normalized_actor = _required(actor, "actor", 200)
    normalized_idempotency = _required(idempotency_key, "idempotency_key", 300)
    key = attempt_key(plan_id, step_key.strip(), normalized_idempotency)
    existing = session.scalar(
        select(ResearchStepAttemptRecord).where(
            ResearchStepAttemptRecord.attempt_key == key
        )
    )
    if existing is not None:
        return existing
    step = _step(session, plan_id, step_key)
    if step.state not in _ATTEMPTABLE_STATES:
        raise ValueError("research step is not eligible for an attempt")
    mode = ResearchStepMode(step.mode)
    state = (
        ResearchStepState.MANUAL_ACTION_REQUIRED
        if mode is ResearchStepMode.MANUAL_LINK
        else ResearchStepState.RUNNING
    )
    record = ResearchStepAttemptRecord(
        id=uuid4(),
        plan_id=plan_id,
        step_id=step.id,
        attempt_key=key,
        mode=mode.value,
        state=state.value,
        actor=normalized_actor,
        external_action_started=False,
        external_action_reference=None,
        error_code=None,
        started_at=current,
        completed_at=None,
        created_at=current,
        updated_at=current,
    )
    session.add(record)
    step.state = state.value
    step.updated_at = current
    session.flush()
    return record


def mark_external_action_started(
    session: Session,
    attempt_id: UUID,
    *,
    reference: str,
    now: datetime,
) -> ResearchStepAttemptRecord:
    current = require_aware_utc(now, field_name="now")
    normalized_reference = _required(reference, "reference", 500)
    attempt = _attempt(session, attempt_id)
    if attempt.mode != ResearchStepMode.AUTOMATED_ADAPTER.value:
        raise ValueError("only an automated-adapter attempt can start an external action")
    if attempt.external_action_started:
        if attempt.external_action_reference != normalized_reference:
            raise ValueError("external action already started with a different reference")
        return attempt
    if attempt.state != ResearchStepState.RUNNING.value:
        raise ValueError("research attempt is not running")
    attempt.external_action_started = True
    attempt.external_action_reference = normalized_reference
    attempt.updated_at = current
    session.flush()
    return attempt


def complete_research_attempt(
    session: Session,
    attempt_id: UUID,
    *,
    now: datetime,
) -> ResearchStepAttemptRecord:
    current = require_aware_utc(now, field_name="now")
    attempt = _attempt(session, attempt_id)
    if attempt.state == ResearchStepState.COMPLETED.value:
        return attempt
    if attempt.state not in {
        ResearchStepState.RUNNING.value,
        ResearchStepState.MANUAL_ACTION_REQUIRED.value,
    }:
        raise ValueError("research attempt cannot be completed from current state")
    attempt.state = ResearchStepState.COMPLETED.value
    attempt.completed_at = current
    attempt.updated_at = current
    step = session.get(ResearchStepRecord, attempt.step_id)
    if step is not None:
        step.state = ResearchStepState.COMPLETED.value
        step.updated_at = current
    session.flush()
    return attempt


def _step(session: Session, plan_id: UUID, step_key: str) -> ResearchStepRecord:
    normalized = _required(step_key, "step_key", 150)
    record = session.scalar(
        select(ResearchStepRecord).where(
            ResearchStepRecord.plan_id == plan_id,
            ResearchStepRecord.step_key == normalized,
        )
    )
    if record is None:
        raise LookupError("research step not found")
    return record


def _attempt(session: Session, attempt_id: UUID) -> ResearchStepAttemptRecord:
    record = session.get(ResearchStepAttemptRecord, attempt_id)
    if record is None:
        raise LookupError("research attempt not found")
    return record


def _required(value: str, field_name: str, maximum: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > maximum:
        raise ValueError(f"{field_name} cannot exceed {maximum} characters")
    return normalized

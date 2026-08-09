from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.research_orchestration.domain import (
    ResearchDecisionType,
    ResearchPlanState,
)
from cip.modules.research_orchestration.infrastructure.hydration import hydrate_plan
from cip.modules.research_orchestration.infrastructure.models import (
    ResearchPlanDecisionRecord,
    ResearchPlanRecord,
)
from cip.modules.research_orchestration.infrastructure.payloads import plan_decision_key
from cip.modules.research_orchestration.infrastructure.plan_persistence import (
    persist_research_plan,
)
from cip.shared.kernel.time import require_aware_utc

_TRANSITIONS: dict[ResearchDecisionType, dict[ResearchPlanState, ResearchPlanState]] = {
    ResearchDecisionType.APPROVE: {
        ResearchPlanState.DRAFT: ResearchPlanState.APPROVED,
        ResearchPlanState.PENDING_REVIEW: ResearchPlanState.APPROVED,
    },
    ResearchDecisionType.REJECT: {
        ResearchPlanState.DRAFT: ResearchPlanState.CANCELLED,
        ResearchPlanState.PENDING_REVIEW: ResearchPlanState.CANCELLED,
    },
    ResearchDecisionType.PAUSE: {
        ResearchPlanState.APPROVED: ResearchPlanState.PAUSED,
        ResearchPlanState.IN_PROGRESS: ResearchPlanState.PAUSED,
    },
    ResearchDecisionType.RESUME: {
        ResearchPlanState.PAUSED: ResearchPlanState.APPROVED,
    },
    ResearchDecisionType.COMPLETE: {
        ResearchPlanState.APPROVED: ResearchPlanState.COMPLETED,
        ResearchPlanState.IN_PROGRESS: ResearchPlanState.COMPLETED,
    },
    ResearchDecisionType.CANCEL: {
        ResearchPlanState.DRAFT: ResearchPlanState.CANCELLED,
        ResearchPlanState.PENDING_REVIEW: ResearchPlanState.CANCELLED,
        ResearchPlanState.APPROVED: ResearchPlanState.CANCELLED,
        ResearchPlanState.IN_PROGRESS: ResearchPlanState.CANCELLED,
        ResearchPlanState.PAUSED: ResearchPlanState.CANCELLED,
    },
}


def apply_research_plan_decision(
    session: Session,
    plan_id: UUID,
    decision_type: ResearchDecisionType,
    *,
    actor: str,
    reason: str,
    now: datetime,
) -> ResearchPlanDecisionRecord:
    current = require_aware_utc(now, field_name="now")
    normalized_actor = _required(actor, "actor", 200)
    normalized_reason = _required(reason, "reason", 1000)
    record = _plan_record(session, plan_id)
    plan = hydrate_plan(record)
    replay = _replayed_decision(
        session,
        plan_id,
        decision_type,
        actor=normalized_actor,
        reason=normalized_reason,
        current_state=plan.state,
    )
    if replay is not None:
        return replay
    target = _target_state(decision_type, plan.state)
    previous_revision = record.current_revision_key
    decision_key = plan_decision_key(
        plan_revision=previous_revision,
        decision_type=decision_type.value,
        actor=normalized_actor,
        reason=normalized_reason,
        previous_state=plan.state.value,
        resulting_state=target.value,
    )
    persist_research_plan(
        session,
        replace(plan, state=target),
        actor=normalized_actor,
        change_reason=f"{decision_type.value}: {normalized_reason}",
        now=current,
    )
    decision = ResearchPlanDecisionRecord(
        id=uuid4(),
        plan_id=plan_id,
        decision_key=decision_key,
        decision_type=decision_type.value,
        actor=normalized_actor,
        reason=normalized_reason,
        previous_state=plan.state.value,
        resulting_state=target.value,
        decided_at=current,
        created_at=current,
    )
    session.add(decision)
    session.flush()
    return decision


def _plan_record(session: Session, plan_id: UUID) -> ResearchPlanRecord:
    record = session.get(ResearchPlanRecord, plan_id)
    if record is None:
        raise LookupError("research plan not found")
    return record


def _target_state(
    decision_type: ResearchDecisionType,
    current: ResearchPlanState,
) -> ResearchPlanState:
    target = _TRANSITIONS[decision_type].get(current)
    if target is None:
        raise ValueError(
            f"research plan cannot {decision_type.value} from {current.value}"
        )
    return target


def _replayed_decision(
    session: Session,
    plan_id: UUID,
    decision_type: ResearchDecisionType,
    *,
    actor: str,
    reason: str,
    current_state: ResearchPlanState,
) -> ResearchPlanDecisionRecord | None:
    return session.scalar(
        select(ResearchPlanDecisionRecord)
        .where(
            ResearchPlanDecisionRecord.plan_id == plan_id,
            ResearchPlanDecisionRecord.decision_type == decision_type.value,
            ResearchPlanDecisionRecord.actor == actor,
            ResearchPlanDecisionRecord.reason == reason,
            ResearchPlanDecisionRecord.resulting_state == current_state.value,
        )
        .order_by(ResearchPlanDecisionRecord.decided_at.desc())
        .limit(1)
    )


def _required(value: str, field_name: str, maximum: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > maximum:
        raise ValueError(f"{field_name} cannot exceed {maximum} characters")
    return normalized

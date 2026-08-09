from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.research_orchestration.domain import (
    ResearchPlan,
    ResearchRuntimeState,
    ResearchStep,
    ResearchStepDecision,
    ResearchUsage,
    evaluate_research_step,
)
from cip.modules.research_orchestration.infrastructure.models import (
    ResearchPlanRecord,
    ResearchStepDecisionRecord,
    ResearchStepRecord,
)
from cip.modules.research_orchestration.infrastructure.payloads import (
    step_decision_key,
    step_definition_key,
    runtime_payload,
    usage_payload,
)
from cip.shared.kernel.time import require_aware_utc


def evaluate_and_persist_step_decision(
    session: Session,
    plan: ResearchPlan,
    step: ResearchStep,
    usage: ResearchUsage,
    runtime: ResearchRuntimeState,
    *,
    now: datetime,
) -> ResearchStepDecision:
    current = require_aware_utc(now, field_name="now")
    plan_record = _plan_record(session, plan.plan_id)
    step_record = _step_record(session, plan.plan_id, step.step_key)
    decision = evaluate_research_step(plan, step, usage, runtime, now=current)
    key = step_decision_key(
        plan_revision=plan_record.current_revision_key,
        step_definition=step_definition_key(plan.plan_id, step),
        usage=usage,
        runtime=runtime,
        decision=decision,
        evaluated_at=current,
    )
    if not _decision_exists(session, key):
        session.add(
            ResearchStepDecisionRecord(
                id=uuid4(),
                plan_id=plan.plan_id,
                step_id=step_record.id,
                decision_key=key,
                allowed=decision.allowed,
                next_state=decision.next_state.value,
                reasons=[reason.value for reason in decision.reasons],
                usage_snapshot=usage_payload(usage),
                runtime_snapshot=runtime_payload(runtime),
                evaluated_at=current,
                created_at=current,
            )
        )
    step_record.state = decision.next_state.value
    step_record.updated_at = current
    session.flush()
    return decision


def _plan_record(session: Session, plan_id: UUID) -> ResearchPlanRecord:
    record = session.get(ResearchPlanRecord, plan_id)
    if record is None:
        raise LookupError("research plan not found")
    return record


def _step_record(session: Session, plan_id: UUID, step_key: str) -> ResearchStepRecord:
    record = session.scalar(
        select(ResearchStepRecord).where(
            ResearchStepRecord.plan_id == plan_id,
            ResearchStepRecord.step_key == step_key,
        )
    )
    if record is None:
        raise LookupError("research step not found")
    return record


def _decision_exists(session: Session, decision_key: str) -> bool:
    return (
        session.scalar(
            select(ResearchStepDecisionRecord.id).where(
                ResearchStepDecisionRecord.decision_key == decision_key
            )
        )
        is not None
    )

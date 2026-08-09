from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.research_orchestration.domain import (
    ResearchStepMode,
    ResearchStepState,
    ResearchUsage,
)
from cip.modules.research_orchestration.infrastructure.models import (
    ResearchStepAttemptRecord,
    ResearchStepRecord,
)


def resolve_research_usage(session: Session, plan_id: object) -> ResearchUsage:
    steps = tuple(
        session.scalars(
            select(ResearchStepRecord).where(ResearchStepRecord.plan_id == plan_id)
        )
    )
    attempts = tuple(
        session.scalars(
            select(ResearchStepAttemptRecord).where(
                ResearchStepAttemptRecord.plan_id == plan_id,
                ResearchStepAttemptRecord.external_action_started.is_(True),
                ResearchStepAttemptRecord.mode == ResearchStepMode.AUTOMATED_ADAPTER.value,
            )
        )
    )
    automated_step_ids = {attempt.step_id for attempt in attempts}
    completed_steps = sum(
        step.state == ResearchStepState.COMPLETED.value for step in steps
    )
    cost_used = sum(
        step.estimated_cost for step in steps if step.id in automated_step_ids
    )
    return ResearchUsage(
        completed_steps=completed_steps,
        automated_steps=len(automated_step_ids),
        cost_used=cost_used,
    )

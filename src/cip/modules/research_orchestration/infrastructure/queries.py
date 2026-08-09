from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cip.modules.research_orchestration.infrastructure.models import (
    ResearchPlanDecisionRecord,
    ResearchPlanRecord,
    ResearchPlanRevisionRecord,
    ResearchResultRecord,
    ResearchStepAttemptRecord,
    ResearchStepDecisionRecord,
    ResearchStepRecord,
)


class ResearchPlanNotFoundError(LookupError):
    pass


def list_research_plans(
    session: Session,
    *,
    limit: int = 100,
    offset: int = 0,
) -> tuple[tuple[ResearchPlanRecord, ...], int]:
    if not 1 <= limit <= 200 or offset < 0:
        raise ValueError("invalid research plan pagination")
    total = int(session.scalar(select(func.count()).select_from(ResearchPlanRecord)) or 0)
    records = tuple(
        session.scalars(
            select(ResearchPlanRecord)
            .order_by(ResearchPlanRecord.updated_at.desc(), ResearchPlanRecord.id)
            .limit(limit)
            .offset(offset)
        )
    )
    return records, total


def get_research_plan(session: Session, plan_id: UUID) -> ResearchPlanRecord:
    record = session.get(ResearchPlanRecord, plan_id)
    if record is None:
        raise ResearchPlanNotFoundError("research plan not found")
    return record


def list_plan_revisions(
    session: Session,
    plan_id: UUID,
    *,
    limit: int = 100,
) -> tuple[ResearchPlanRevisionRecord, ...]:
    return tuple(
        session.scalars(
            select(ResearchPlanRevisionRecord)
            .where(ResearchPlanRevisionRecord.plan_id == plan_id)
            .order_by(ResearchPlanRevisionRecord.created_at.desc())
            .limit(limit)
        )
    )


def list_plan_steps(session: Session, plan_id: UUID) -> tuple[ResearchStepRecord, ...]:
    return tuple(
        session.scalars(
            select(ResearchStepRecord)
            .where(ResearchStepRecord.plan_id == plan_id)
            .order_by(ResearchStepRecord.sequence, ResearchStepRecord.id)
        )
    )


def get_plan_step(
    session: Session,
    plan_id: UUID,
    step_key: str,
) -> ResearchStepRecord:
    record = session.scalar(
        select(ResearchStepRecord).where(
            ResearchStepRecord.plan_id == plan_id,
            ResearchStepRecord.step_key == step_key,
        )
    )
    if record is None:
        raise LookupError("research step not found")
    return record


def list_plan_decisions(
    session: Session,
    plan_id: UUID,
    *,
    limit: int = 100,
) -> tuple[ResearchPlanDecisionRecord, ...]:
    return tuple(
        session.scalars(
            select(ResearchPlanDecisionRecord)
            .where(ResearchPlanDecisionRecord.plan_id == plan_id)
            .order_by(ResearchPlanDecisionRecord.decided_at.desc())
            .limit(limit)
        )
    )


def list_step_decisions(
    session: Session,
    plan_id: UUID,
    *,
    limit: int = 200,
) -> tuple[ResearchStepDecisionRecord, ...]:
    return tuple(
        session.scalars(
            select(ResearchStepDecisionRecord)
            .where(ResearchStepDecisionRecord.plan_id == plan_id)
            .order_by(ResearchStepDecisionRecord.evaluated_at.desc())
            .limit(limit)
        )
    )


def list_step_attempts(
    session: Session,
    plan_id: UUID,
    *,
    limit: int = 200,
) -> tuple[ResearchStepAttemptRecord, ...]:
    return tuple(
        session.scalars(
            select(ResearchStepAttemptRecord)
            .where(ResearchStepAttemptRecord.plan_id == plan_id)
            .order_by(ResearchStepAttemptRecord.started_at.desc())
            .limit(limit)
        )
    )


def list_research_results(
    session: Session,
    plan_id: UUID,
    *,
    limit: int = 200,
) -> tuple[ResearchResultRecord, ...]:
    return tuple(
        session.scalars(
            select(ResearchResultRecord)
            .where(ResearchResultRecord.plan_id == plan_id)
            .order_by(ResearchResultRecord.recorded_at.desc())
            .limit(limit)
        )
    )

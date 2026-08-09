from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.research_orchestration.domain import ResearchStep, ResearchStepState
from cip.modules.research_orchestration.infrastructure.models import ResearchStepRecord
from cip.modules.research_orchestration.infrastructure.payloads import (
    step_definition_key,
    step_payload,
)
from cip.shared.kernel.time import require_aware_utc


def persist_research_step(
    session: Session,
    plan_id: UUID,
    step: ResearchStep,
    *,
    now: datetime,
) -> ResearchStepRecord:
    current = require_aware_utc(now, field_name="now")
    existing = session.scalar(
        select(ResearchStepRecord).where(
            ResearchStepRecord.plan_id == plan_id,
            ResearchStepRecord.step_key == step.step_key,
        )
    )
    if existing is not None:
        _assert_same_definition(existing, plan_id, step)
        return existing
    if _sequence_exists(session, plan_id, step.sequence):
        raise ValueError("research step sequence already exists for plan")
    record = ResearchStepRecord(
        id=uuid4(),
        plan_id=plan_id,
        state=ResearchStepState.PLANNED.value,
        created_at=current,
        updated_at=current,
        **step_payload(step),
    )
    session.add(record)
    session.flush()
    return record


def _sequence_exists(session: Session, plan_id: UUID, sequence: int) -> bool:
    return (
        session.scalar(
            select(ResearchStepRecord.id).where(
                ResearchStepRecord.plan_id == plan_id,
                ResearchStepRecord.sequence == sequence,
            )
        )
        is not None
    )


def _assert_same_definition(
    record: ResearchStepRecord,
    plan_id: UUID,
    step: ResearchStep,
) -> None:
    expected = step_definition_key(plan_id, step)
    persisted = ResearchStep(
        step_key=record.step_key,
        sequence=record.sequence,
        source_id=record.source_id,
        tool_id=record.tool_id,
        mode=step.mode.__class__(record.mode),
        purpose=record.purpose,
        data_category=step.data_category.__class__(record.data_category),
        estimated_cost=record.estimated_cost,
        risk_level=step.risk_level.__class__(record.risk_level),
        target_url=record.target_url,
        query_text=record.query_text,
        ingestion_path_id=record.ingestion_path_id,
    )
    if step_definition_key(plan_id, persisted) != expected:
        raise ValueError("research step definition cannot mutate under the same step_key")

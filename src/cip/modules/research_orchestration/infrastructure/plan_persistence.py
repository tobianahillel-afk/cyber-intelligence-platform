from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.research_orchestration.domain import ResearchPlan
from cip.modules.research_orchestration.infrastructure.models import (
    ResearchPlanRecord,
    ResearchPlanRevisionRecord,
)
from cip.modules.research_orchestration.infrastructure.payloads import plan_revision_key
from cip.shared.kernel.time import require_aware_utc


def persist_research_plan(
    session: Session,
    plan: ResearchPlan,
    *,
    actor: str,
    change_reason: str,
    now: datetime,
) -> ResearchPlanRecord:
    current = require_aware_utc(now, field_name="now")
    normalized_actor = _required(actor, "actor", 200)
    normalized_reason = _required(change_reason, "change_reason", 1000)
    revision_key = plan_revision_key(plan)
    record = session.get(ResearchPlanRecord, plan.plan_id)
    if record is None:
        record = _new_plan_record(plan, revision_key, current)
        session.add(record)
        session.flush()
    if not _revision_exists(session, revision_key):
        session.add(
            _new_revision_record(
                plan,
                revision_key,
                actor=normalized_actor,
                change_reason=normalized_reason,
                now=current,
            )
        )
    if record.current_revision_key != revision_key:
        _apply_plan(record, plan, revision_key, current)
    session.flush()
    return record


def _revision_exists(session: Session, revision_key: str) -> bool:
    return (
        session.scalar(
            select(ResearchPlanRevisionRecord.id).where(
                ResearchPlanRevisionRecord.revision_key == revision_key
            )
        )
        is not None
    )


def _new_plan_record(
    plan: ResearchPlan,
    revision_key: str,
    now: datetime,
) -> ResearchPlanRecord:
    return ResearchPlanRecord(
        id=plan.plan_id,
        current_revision_key=revision_key,
        created_at=now,
        updated_at=now,
        **_plan_values(plan),
    )


def _new_revision_record(
    plan: ResearchPlan,
    revision_key: str,
    *,
    actor: str,
    change_reason: str,
    now: datetime,
) -> ResearchPlanRevisionRecord:
    return ResearchPlanRevisionRecord(
        id=uuid4(),
        plan_id=plan.plan_id,
        revision_key=revision_key,
        budget=_budget_values(plan),
        actor=actor,
        change_reason=change_reason,
        created_at=now,
        **_revision_values(plan),
    )


def _apply_plan(
    record: ResearchPlanRecord,
    plan: ResearchPlan,
    revision_key: str,
    now: datetime,
) -> None:
    for field_name, value in _plan_values(plan).items():
        setattr(record, field_name, value)
    record.current_revision_key = revision_key
    record.updated_at = now


def _plan_values(plan: ResearchPlan) -> dict[str, object]:
    return {
        "question": plan.question,
        "purpose": plan.purpose,
        "data_category": plan.data_category.value,
        "state": plan.state.value,
        **_budget_values(plan),
        **_scope_values(plan),
        "max_risk_level": plan.max_risk_level.value,
        "expires_at": plan.expires_at,
    }


def _revision_values(plan: ResearchPlan) -> dict[str, object]:
    return {
        "question": plan.question,
        "purpose": plan.purpose,
        "data_category": plan.data_category.value,
        "state": plan.state.value,
        **_scope_values(plan),
        "max_risk_level": plan.max_risk_level.value,
        "expires_at": plan.expires_at,
    }


def _budget_values(plan: ResearchPlan) -> dict[str, object]:
    return {
        "max_steps": plan.budget.max_steps,
        "max_automated_steps": plan.budget.max_automated_steps,
        "max_total_cost": plan.budget.max_total_cost,
        "max_step_cost": plan.budget.max_step_cost,
    }


def _scope_values(plan: ResearchPlan) -> dict[str, object]:
    return {
        "allowed_source_ids": sorted(plan.allowed_source_ids),
        "allowed_tool_ids": sorted(plan.allowed_tool_ids),
        "approved_step_keys": sorted(plan.approved_step_keys),
        "allowed_hosts": sorted(plan.allowed_hosts),
        "allowed_path_prefixes": list(plan.allowed_path_prefixes),
    }


def _required(value: str, field_name: str, maximum: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > maximum:
        raise ValueError(f"{field_name} cannot exceed {maximum} characters")
    return normalized

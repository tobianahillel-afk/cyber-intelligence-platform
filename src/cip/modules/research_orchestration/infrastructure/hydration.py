from __future__ import annotations

from cip.modules.research_orchestration.domain import (
    ResearchBudget,
    ResearchPlan,
    ResearchPlanState,
    ResearchRiskLevel,
    ResearchStep,
    ResearchStepMode,
)
from cip.modules.research_orchestration.infrastructure.models import (
    ResearchPlanRecord,
    ResearchStepRecord,
)
from cip.modules.source_governance.domain.models import DataCategory


def hydrate_plan(record: ResearchPlanRecord) -> ResearchPlan:
    return ResearchPlan(
        plan_id=record.id,
        question=record.question,
        purpose=record.purpose,
        data_category=DataCategory(record.data_category),
        state=ResearchPlanState(record.state),
        budget=ResearchBudget(
            max_steps=record.max_steps,
            max_automated_steps=record.max_automated_steps,
            max_total_cost=record.max_total_cost,
            max_step_cost=record.max_step_cost,
        ),
        allowed_source_ids=frozenset(record.allowed_source_ids),
        allowed_tool_ids=frozenset(record.allowed_tool_ids),
        approved_step_keys=frozenset(record.approved_step_keys),
        allowed_hosts=frozenset(record.allowed_hosts),
        allowed_path_prefixes=tuple(record.allowed_path_prefixes),
        max_risk_level=ResearchRiskLevel(record.max_risk_level),
        expires_at=record.expires_at,
    )


def hydrate_step(record: ResearchStepRecord) -> ResearchStep:
    return ResearchStep(
        step_key=record.step_key,
        sequence=record.sequence,
        source_id=record.source_id,
        tool_id=record.tool_id,
        mode=ResearchStepMode(record.mode),
        purpose=record.purpose,
        data_category=DataCategory(record.data_category),
        estimated_cost=record.estimated_cost,
        risk_level=ResearchRiskLevel(record.risk_level),
        target_url=record.target_url,
        query_text=record.query_text,
        ingestion_path_id=record.ingestion_path_id,
    )

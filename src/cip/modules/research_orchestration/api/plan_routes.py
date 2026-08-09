from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from cip.modules.research_orchestration.api.schemas import (
    ResearchAttemptResponse,
    ResearchPlanDecisionRequest,
    ResearchPlanDecisionResponse,
    ResearchPlanDetail,
    ResearchPlanListResponse,
    ResearchPlanResponse,
    ResearchPlanRevisionResponse,
    ResearchPlanUpsertRequest,
    ResearchResultResponse,
    ResearchStepDecisionResponse,
    ResearchStepResponse,
    ResearchUsageResponse,
)
from cip.modules.research_orchestration.domain import (
    ResearchBudget,
    ResearchPlan,
    ResearchPlanState,
)
from cip.modules.research_orchestration.infrastructure.hydration import hydrate_plan
from cip.modules.research_orchestration.infrastructure.plan_control import (
    apply_research_plan_decision,
)
from cip.modules.research_orchestration.infrastructure.plan_persistence import (
    persist_research_plan,
)
from cip.modules.research_orchestration.infrastructure.queries import (
    ResearchPlanNotFoundError,
    get_research_plan,
    list_plan_decisions,
    list_plan_revisions,
    list_plan_steps,
    list_research_plans,
    list_research_results,
    list_step_attempts,
    list_step_decisions,
)
from cip.modules.research_orchestration.infrastructure.usage import resolve_research_usage
from cip.shared.persistence.dependencies import get_database_session

router = APIRouter()
SessionDependency = Annotated[Session, Depends(get_database_session)]
_TERMINAL_STATES = {ResearchPlanState.COMPLETED, ResearchPlanState.CANCELLED}


@router.get("/plans", response_model=ResearchPlanListResponse)
def list_plans(
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ResearchPlanListResponse:
    records, total = list_research_plans(session, limit=limit, offset=offset)
    return ResearchPlanListResponse(
        items=[ResearchPlanResponse.model_validate(record) for record in records],
        total=total,
    )


@router.get("/plans/{plan_id}", response_model=ResearchPlanDetail)
def get_plan(plan_id: UUID, session: SessionDependency) -> ResearchPlanDetail:
    try:
        record = get_research_plan(session, plan_id)
    except ResearchPlanNotFoundError as exc:
        raise _not_found() from exc
    usage = resolve_research_usage(session, plan_id)
    return ResearchPlanDetail(
        plan=ResearchPlanResponse.model_validate(record),
        usage=ResearchUsageResponse(
            completed_steps=usage.completed_steps,
            automated_steps=usage.automated_steps,
            cost_used=usage.cost_used,
        ),
        revisions=[
            ResearchPlanRevisionResponse.model_validate(item)
            for item in list_plan_revisions(session, plan_id)
        ],
        steps=[
            ResearchStepResponse.model_validate(item)
            for item in list_plan_steps(session, plan_id)
        ],
        plan_decisions=[
            ResearchPlanDecisionResponse.model_validate(item)
            for item in list_plan_decisions(session, plan_id)
        ],
        step_decisions=[
            ResearchStepDecisionResponse.model_validate(item)
            for item in list_step_decisions(session, plan_id)
        ],
        attempts=[
            ResearchAttemptResponse.model_validate(item)
            for item in list_step_attempts(session, plan_id)
        ],
        results=[
            ResearchResultResponse.model_validate(item)
            for item in list_research_results(session, plan_id)
        ],
    )


@router.put("/plans/{plan_id}", response_model=ResearchPlanResponse)
def upsert_plan(
    plan_id: UUID,
    request: ResearchPlanUpsertRequest,
    session: SessionDependency,
) -> ResearchPlanResponse:
    try:
        state = _existing_state(session, plan_id)
        record = persist_research_plan(
            session,
            _plan(plan_id, request, state=state),
            actor=request.actor,
            change_reason=request.change_reason,
            now=datetime.now(UTC),
        )
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise _unprocessable(str(exc)) from exc
    return ResearchPlanResponse.model_validate(record)


@router.post(
    "/plans/{plan_id}/decision",
    response_model=ResearchPlanDecisionResponse,
)
def decide_plan(
    plan_id: UUID,
    request: ResearchPlanDecisionRequest,
    session: SessionDependency,
) -> ResearchPlanDecisionResponse:
    try:
        decision = apply_research_plan_decision(
            session,
            plan_id,
            request.decision_type,
            actor=request.actor,
            reason=request.reason,
            now=datetime.now(UTC),
        )
        session.commit()
    except LookupError as exc:
        session.rollback()
        raise _not_found() from exc
    except ValueError as exc:
        session.rollback()
        raise _unprocessable(str(exc)) from exc
    return ResearchPlanDecisionResponse.model_validate(decision)


def _existing_state(session: Session, plan_id: UUID) -> ResearchPlanState:
    try:
        current = hydrate_plan(get_research_plan(session, plan_id))
    except ResearchPlanNotFoundError:
        return ResearchPlanState.DRAFT
    if current.state in _TERMINAL_STATES:
        raise ValueError("terminal research plan cannot be revised")
    return current.state


def _plan(
    plan_id: UUID,
    request: ResearchPlanUpsertRequest,
    *,
    state: ResearchPlanState,
) -> ResearchPlan:
    return ResearchPlan(
        plan_id=plan_id,
        question=request.question,
        purpose=request.purpose,
        data_category=request.data_category,
        state=state,
        budget=ResearchBudget(
            max_steps=request.budget.max_steps,
            max_automated_steps=request.budget.max_automated_steps,
            max_total_cost=request.budget.max_total_cost,
            max_step_cost=request.budget.max_step_cost,
        ),
        allowed_source_ids=frozenset(request.allowed_source_ids),
        allowed_tool_ids=frozenset(request.allowed_tool_ids),
        approved_step_keys=frozenset(request.approved_step_keys),
        allowed_hosts=frozenset(request.allowed_hosts),
        allowed_path_prefixes=tuple(request.allowed_path_prefixes),
        max_risk_level=request.max_risk_level,
        expires_at=request.expires_at,
    )


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="research plan not found",
    )


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=detail,
    )

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.research_orchestration.api.schemas import (
    ResearchAttemptCreateRequest,
    ResearchAttemptResponse,
    ResearchEvaluationResponse,
    ResearchResultCreateRequest,
    ResearchResultResponse,
    ResearchRuntimeResponse,
    ResearchStepCreateRequest,
    ResearchStepResponse,
    ResearchUsageResponse,
)
from cip.modules.research_orchestration.domain import ResearchStep
from cip.modules.research_orchestration.infrastructure.attempt_persistence import (
    begin_research_attempt,
    complete_research_attempt,
)
from cip.modules.research_orchestration.infrastructure.decision_persistence import (
    evaluate_and_persist_step_decision,
)
from cip.modules.research_orchestration.infrastructure.hydration import (
    hydrate_plan,
    hydrate_step,
)
from cip.modules.research_orchestration.infrastructure.models import (
    ResearchStepAttemptRecord,
)
from cip.modules.research_orchestration.infrastructure.payloads import attempt_key
from cip.modules.research_orchestration.infrastructure.queries import (
    ResearchPlanNotFoundError,
    get_plan_step,
    get_research_plan,
)
from cip.modules.research_orchestration.infrastructure.result_persistence import (
    ResearchResultCapture,
    record_research_result,
)
from cip.modules.research_orchestration.infrastructure.result_validation import (
    validate_research_result_capture,
)
from cip.modules.research_orchestration.infrastructure.runtime_state import (
    resolve_research_runtime,
)
from cip.modules.research_orchestration.infrastructure.step_persistence import (
    persist_research_step,
)
from cip.modules.research_orchestration.infrastructure.usage import resolve_research_usage
from cip.shared.persistence.dependencies import get_database_session

router = APIRouter()
SessionDependency = Annotated[Session, Depends(get_database_session)]


@router.post("/plans/{plan_id}/steps", response_model=ResearchStepResponse)
def create_step(
    plan_id: UUID,
    request: ResearchStepCreateRequest,
    session: SessionDependency,
) -> ResearchStepResponse:
    try:
        get_research_plan(session, plan_id)
        record = persist_research_step(
            session,
            plan_id,
            _step(request),
            now=datetime.now(UTC),
        )
        session.commit()
    except ResearchPlanNotFoundError as exc:
        session.rollback()
        raise _plan_not_found() from exc
    except ValueError as exc:
        session.rollback()
        raise _unprocessable(str(exc)) from exc
    return ResearchStepResponse.model_validate(record)


@router.post(
    "/plans/{plan_id}/steps/{step_key}/evaluate",
    response_model=ResearchEvaluationResponse,
)
def evaluate_step(
    plan_id: UUID,
    step_key: str,
    session: SessionDependency,
) -> ResearchEvaluationResponse:
    try:
        response = _evaluate(session, plan_id, step_key, now=datetime.now(UTC))
        session.commit()
        return response
    except ResearchPlanNotFoundError as exc:
        session.rollback()
        raise _plan_not_found() from exc
    except LookupError as exc:
        session.rollback()
        raise _step_not_found() from exc
    except ValueError as exc:
        session.rollback()
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/plans/{plan_id}/steps/{step_key}/attempts",
    response_model=ResearchAttemptResponse,
)
def create_attempt(
    plan_id: UUID,
    step_key: str,
    request: ResearchAttemptCreateRequest,
    session: SessionDependency,
) -> ResearchAttemptResponse:
    try:
        existing = _existing_attempt(
            session,
            plan_id,
            step_key,
            request.idempotency_key,
        )
        if existing is not None:
            return ResearchAttemptResponse.model_validate(existing)
        evaluation = _evaluate(session, plan_id, step_key, now=datetime.now(UTC))
        if not evaluation.allowed:
            session.commit()
            raise _unprocessable("research step is not eligible for an attempt")
        attempt = begin_research_attempt(
            session,
            plan_id,
            step_key,
            actor=request.actor,
            idempotency_key=request.idempotency_key,
            now=datetime.now(UTC),
        )
        session.commit()
    except ResearchPlanNotFoundError as exc:
        session.rollback()
        raise _plan_not_found() from exc
    except LookupError as exc:
        session.rollback()
        raise _step_not_found() from exc
    except ValueError as exc:
        session.rollback()
        raise _unprocessable(str(exc)) from exc
    return ResearchAttemptResponse.model_validate(attempt)


@router.post(
    "/plans/{plan_id}/attempts/{attempt_id}/complete",
    response_model=ResearchAttemptResponse,
)
def complete_attempt(
    plan_id: UUID,
    attempt_id: UUID,
    session: SessionDependency,
) -> ResearchAttemptResponse:
    try:
        attempt = session.get(ResearchStepAttemptRecord, attempt_id)
        if attempt is None or attempt.plan_id != plan_id:
            raise LookupError("research attempt not found")
        record = complete_research_attempt(
            session,
            attempt_id,
            now=datetime.now(UTC),
        )
        session.commit()
    except LookupError as exc:
        session.rollback()
        raise _attempt_not_found() from exc
    except ValueError as exc:
        session.rollback()
        raise _unprocessable(str(exc)) from exc
    return ResearchAttemptResponse.model_validate(record)


@router.post(
    "/plans/{plan_id}/steps/{step_key}/results",
    response_model=ResearchResultResponse,
)
def create_result(
    plan_id: UUID,
    step_key: str,
    request: ResearchResultCreateRequest,
    session: SessionDependency,
) -> ResearchResultResponse:
    try:
        get_research_plan(session, plan_id)
        step_record = get_plan_step(session, plan_id, step_key)
        capture = _capture(request)
        validate_research_result_capture(
            session,
            capture,
            expected_source_id=step_record.source_id,
        )
        result = record_research_result(
            session,
            plan_id,
            step_key,
            capture,
            now=datetime.now(UTC),
        )
        session.commit()
    except ResearchPlanNotFoundError as exc:
        session.rollback()
        raise _plan_not_found() from exc
    except LookupError as exc:
        session.rollback()
        raise _reference_not_found(str(exc)) from exc
    except ValueError as exc:
        session.rollback()
        raise _unprocessable(str(exc)) from exc
    return ResearchResultResponse.model_validate(result)


def _evaluate(
    session: Session,
    plan_id: UUID,
    step_key: str,
    *,
    now: datetime,
) -> ResearchEvaluationResponse:
    plan = hydrate_plan(get_research_plan(session, plan_id))
    step = hydrate_step(get_plan_step(session, plan_id, step_key))
    usage = resolve_research_usage(session, plan_id)
    runtime = resolve_research_runtime(session, plan, step, now=now)
    decision = evaluate_and_persist_step_decision(
        session,
        plan,
        step,
        usage,
        runtime,
        now=now,
    )
    return ResearchEvaluationResponse(
        allowed=decision.allowed,
        next_state=decision.next_state.value,
        reasons=[reason.value for reason in decision.reasons],
        usage=ResearchUsageResponse(
            completed_steps=usage.completed_steps,
            automated_steps=usage.automated_steps,
            cost_used=usage.cost_used,
        ),
        runtime=ResearchRuntimeResponse(
            source_authorized=runtime.source_authorized,
            source_executable=runtime.source_executable,
            adapter_capability_present=runtime.adapter_capability_present,
            manual_link_allowed=runtime.manual_link_allowed,
            ingestion_path_approved=runtime.ingestion_path_approved,
            quota_remaining=runtime.quota_remaining,
        ),
    )


def _existing_attempt(
    session: Session,
    plan_id: UUID,
    step_key: str,
    idempotency_key: str,
) -> ResearchStepAttemptRecord | None:
    key = attempt_key(plan_id, step_key.strip(), idempotency_key.strip())
    return session.scalar(
        select(ResearchStepAttemptRecord).where(
            ResearchStepAttemptRecord.attempt_key == key
        )
    )


def _step(request: ResearchStepCreateRequest) -> ResearchStep:
    return ResearchStep(
        step_key=request.step_key,
        sequence=request.sequence,
        source_id=request.source_id,
        tool_id=request.tool_id,
        mode=request.mode,
        purpose=request.purpose,
        data_category=request.data_category,
        estimated_cost=request.estimated_cost,
        risk_level=request.risk_level,
        target_url=request.target_url,
        query_text=request.query_text,
        ingestion_path_id=request.ingestion_path_id,
    )


def _capture(request: ResearchResultCreateRequest) -> ResearchResultCapture:
    return ResearchResultCapture(
        attempt_id=request.attempt_id,
        result_type=request.result_type,
        evidence_reference=request.evidence_reference,
        provenance_reference=request.provenance_reference,
        source_id=request.source_id,
        summary=request.summary,
        recorded_by=request.recorded_by,
    )


def _plan_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="research plan not found")


def _step_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="research step not found")


def _attempt_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="research attempt not found",
    )


def _reference_not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=detail,
    )

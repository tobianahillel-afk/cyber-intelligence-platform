from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from cip.modules.conditional_integrations.api.schemas import (
    ApprovalResponse,
    ApprovalRevisionResponse,
    ApprovalUpsertRequest,
    ConditionalProviderDetail,
    ConditionalProviderListResponse,
    ConditionalProviderSummary,
    ConditionalProviderValueResponse,
    ControlDecisionResponse,
    EligibilityRequest,
    ExecutionDecisionResponse,
    ProviderControlRequest,
    RuntimeControlResponse,
    SourceValueSummaryResponse,
)
from cip.modules.conditional_integrations.application.value import (
    summarize_conditional_provider_value,
)
from cip.modules.conditional_integrations.domain import (
    ConditionalExecutionRequest,
    ProviderApprovalDossier,
    ProviderControlDecision,
)
from cip.modules.conditional_integrations.infrastructure.approval_persistence import (
    persist_provider_approval,
)
from cip.modules.conditional_integrations.infrastructure.control_persistence import (
    apply_persisted_control_decision,
)
from cip.modules.conditional_integrations.infrastructure.execution_audit import (
    evaluate_and_audit_conditional_execution,
)
from cip.modules.conditional_integrations.infrastructure.queries import (
    ConditionalProviderNotFoundError,
    get_approval,
    get_runtime_control,
    list_approvals,
    list_control_decisions,
    list_execution_decisions,
    list_revisions,
)
from cip.modules.conditional_integrations.infrastructure.runtime_dependencies import (
    resolve_runtime_dependencies,
)
from cip.modules.source_portfolio.api.dependencies import require_control_plane
from cip.modules.source_portfolio.application.value import SourceValueSummary
from cip.shared.persistence.dependencies import get_database_session

router = APIRouter(
    prefix="/v1/conditional-integrations",
    tags=["conditional-integrations"],
    dependencies=[Depends(require_control_plane)],
)
SessionDependency = Annotated[Session, Depends(get_database_session)]


@router.get("/providers", response_model=ConditionalProviderListResponse)
def list_conditional_providers(
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ConditionalProviderListResponse:
    records, total = list_approvals(session, limit=limit, offset=offset)
    return ConditionalProviderListResponse(
        items=[_summary(session, record.source_id) for record in records],
        total=total,
    )


@router.get("/providers/{source_id}", response_model=ConditionalProviderDetail)
def get_conditional_provider(
    source_id: str,
    session: SessionDependency,
) -> ConditionalProviderDetail:
    try:
        approval = get_approval(session, source_id)
    except ConditionalProviderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="provider not found",
        ) from exc
    control = get_runtime_control(session, source_id)
    return ConditionalProviderDetail(
        approval=ApprovalResponse.model_validate(approval),
        control=RuntimeControlResponse.model_validate(control) if control else None,
        revisions=[
            ApprovalRevisionResponse.model_validate(record)
            for record in list_revisions(session, approval.id)
        ],
        control_decisions=(
            [
                ControlDecisionResponse.model_validate(record)
                for record in list_control_decisions(session, control.id)
            ]
            if control
            else []
        ),
        execution_decisions=[
            ExecutionDecisionResponse.model_validate(record)
            for record in list_execution_decisions(session, approval.id)
        ],
    )


@router.get(
    "/providers/{source_id}/value",
    response_model=ConditionalProviderValueResponse,
)
def get_conditional_provider_value(
    source_id: str,
    session: SessionDependency,
) -> ConditionalProviderValueResponse:
    try:
        get_approval(session, source_id)
    except ConditionalProviderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="provider not found",
        ) from exc
    summary = summarize_conditional_provider_value(session, source_id)
    return ConditionalProviderValueResponse(
        source_id=summary.source_id,
        evidence_available=summary.evidence_available,
        source=_source_value_response(summary.source),
        portfolio_without_source=_source_value_response(summary.portfolio_without_source),
    )


@router.put("/providers/{source_id}/approval", response_model=ApprovalResponse)
def upsert_conditional_provider_approval(
    source_id: str,
    request: ApprovalUpsertRequest,
    session: SessionDependency,
) -> ApprovalResponse:
    try:
        dossier = _dossier(source_id, request)
        record = persist_provider_approval(
            session,
            dossier,
            actor=request.actor,
            change_reason=request.change_reason,
            now=datetime.now(UTC),
        )
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return ApprovalResponse.model_validate(record)


@router.post("/providers/{source_id}/control", response_model=RuntimeControlResponse)
def apply_provider_control(
    source_id: str,
    request: ProviderControlRequest,
    session: SessionDependency,
) -> RuntimeControlResponse:
    now = datetime.now(UTC)
    decision = ProviderControlDecision(
        source_id=source_id,
        action=request.action,
        actor=request.actor,
        reason=request.reason,
        decided_at=now,
    )
    try:
        record = apply_persisted_control_decision(session, decision, now=now)
        session.commit()
    except LookupError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="provider not found",
        ) from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return RuntimeControlResponse.model_validate(record)


@router.post(
    "/providers/{source_id}/eligibility",
    response_model=ExecutionDecisionResponse,
)
def evaluate_provider_eligibility(
    source_id: str,
    request: EligibilityRequest,
    session: SessionDependency,
) -> ExecutionDecisionResponse:
    now = datetime.now(UTC)
    execution_request = ConditionalExecutionRequest(
        source_id=source_id,
        access_method=request.access_method,
        purpose=request.purpose,
        data_category=request.data_category,
        target_url=request.target_url,
        requested_scopes=frozenset(request.requested_scopes),
        requested_fields=frozenset(request.requested_fields),
        retention_days=request.retention_days,
        automated=request.automated,
        store_raw_content=request.store_raw_content,
        account_reference=request.account_reference,
    )
    try:
        dependencies = resolve_runtime_dependencies(
            session,
            execution_request,
            now=now,
        )
        evaluate_and_audit_conditional_execution(
            session,
            execution_request,
            dependencies,
            now=now,
        )
        approval = get_approval(session, source_id)
        record = list_execution_decisions(session, approval.id, limit=1)[0]
        session.commit()
    except LookupError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="provider not found",
        ) from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return ExecutionDecisionResponse.model_validate(record)


def _source_value_response(summary: SourceValueSummary) -> SourceValueSummaryResponse:
    return SourceValueSummaryResponse(
        executions=summary.executions,
        modified_executions=summary.modified_executions,
        observations_written=summary.observations_written,
        commercial_projections=summary.commercial_projections,
        identity_projections=summary.identity_projections,
        request_cost=summary.request_cost,
    )


def _summary(session: Session, source_id: str) -> ConditionalProviderSummary:
    approval = get_approval(session, source_id)
    control = get_runtime_control(session, source_id)
    return ConditionalProviderSummary(
        approval=ApprovalResponse.model_validate(approval),
        control=RuntimeControlResponse.model_validate(control) if control else None,
    )


def _dossier(source_id: str, request: ApprovalUpsertRequest) -> ProviderApprovalDossier:
    return ProviderApprovalDossier(
        source_id=source_id,
        provider_kind=request.provider_kind,
        access_method=request.access_method,
        state=request.state,
        authorization_document_reference=request.authorization_document_reference,
        licence_reference=request.licence_reference,
        terms_reference=request.terms_reference,
        terms_state=request.terms_state,
        approved_scopes=frozenset(request.approved_scopes),
        approved_fields=frozenset(request.approved_fields),
        approved_purposes=frozenset(request.approved_purposes),
        approved_data_categories=frozenset(request.approved_data_categories),
        retention_days=request.retention_days,
        automated_collection_allowed=request.automated_collection_allowed,
        account_reference=request.account_reference,
        reviewed_at=request.reviewed_at,
        review_due_at=request.review_due_at,
        expires_at=request.expires_at,
        revoked_at=request.revoked_at,
        paused_reason=request.paused_reason,
    )

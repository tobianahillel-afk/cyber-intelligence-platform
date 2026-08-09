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
    ControlDecisionResponse,
    ExecutionDecisionResponse,
    ProviderControlRequest,
    RuntimeControlResponse,
)
from cip.modules.conditional_integrations.domain import (
    ProviderApprovalDossier,
    ProviderControlDecision,
)
from cip.modules.conditional_integrations.infrastructure.approval_persistence import (
    persist_provider_approval,
)
from cip.modules.conditional_integrations.infrastructure.control_persistence import (
    apply_persisted_control_decision,
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
from cip.modules.source_portfolio.api.dependencies import require_control_plane_access
from cip.shared.persistence.session import get_session

router = APIRouter(
    prefix="/v1/conditional-integrations",
    tags=["conditional-integrations"],
    dependencies=[Depends(require_control_plane_access)],
)


@router.get("/providers", response_model=ConditionalProviderListResponse)
def list_conditional_providers(
    session: Annotated[Session, Depends(get_session)],
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
    session: Annotated[Session, Depends(get_session)],
) -> ConditionalProviderDetail:
    try:
        approval = get_approval(session, source_id)
    except ConditionalProviderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="provider not found") from exc
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


@router.put("/providers/{source_id}/approval", response_model=ApprovalResponse)
def upsert_conditional_provider_approval(
    source_id: str,
    request: ApprovalUpsertRequest,
    session: Annotated[Session, Depends(get_session)],
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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return ApprovalResponse.model_validate(record)


@router.post("/providers/{source_id}/control", response_model=RuntimeControlResponse)
def apply_provider_control(
    source_id: str,
    request: ProviderControlRequest,
    session: Annotated[Session, Depends(get_session)],
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="provider not found") from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return RuntimeControlResponse.model_validate(record)


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

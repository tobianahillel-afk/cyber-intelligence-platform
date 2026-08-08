from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.corporate_graph.api.schemas import (
    BlastRadiusResponse,
    GraphNodeDetailResponse,
    GraphNodePageResponse,
    GraphRefreshResponse,
    ResolutionCandidateDetailResponse,
    ResolutionCandidatePageResponse,
    ResolutionDecisionRequest,
)
from cip.modules.corporate_graph.application.view_models import GraphNodeFilters
from cip.modules.corporate_graph.domain.models import GraphNodeType
from cip.modules.corporate_graph.domain.resolution import (
    ResolutionDecision,
    ResolutionDecisionType,
)
from cip.modules.corporate_graph.infrastructure.blast_radius_queries import (
    build_blast_radius_preview,
)
from cip.modules.corporate_graph.infrastructure.errors import (
    GraphNodeNotFoundError,
    ResolutionCandidateNotFoundError,
)
from cip.modules.corporate_graph.infrastructure.models import EntityResolutionBindingRecord
from cip.modules.corporate_graph.infrastructure.queries import (
    get_graph_node_detail,
    get_resolution_candidate_detail,
    list_graph_nodes,
    list_resolution_candidates,
)
from cip.modules.corporate_graph.infrastructure.refresh import refresh_corporate_graph
from cip.modules.corporate_graph.infrastructure.resolution_persistence import (
    record_resolution_decision,
)
from cip.modules.source_portfolio.api.dependencies import require_control_plane
from cip.shared.kernel.time import utc_now
from cip.shared.persistence.dependencies import get_database_session

router = APIRouter(
    prefix="/v1/graph",
    tags=["corporate-graph"],
    dependencies=[Depends(require_control_plane)],
)
SessionDependency = Annotated[Session, Depends(get_database_session)]


def _node_filters(
    node_type: GraphNodeType | None = None,
    organization_id: UUID | None = None,
    current: bool | None = None,
    suppressed: bool | None = None,
    query: Annotated[str | None, Query(alias="q", max_length=200)] = None,
) -> GraphNodeFilters:
    return GraphNodeFilters(
        node_type=node_type.value if node_type else None,
        organization_id=organization_id,
        current=current,
        suppressed=suppressed,
        query=query,
    )


NodeFiltersDependency = Annotated[GraphNodeFilters, Depends(_node_filters)]


@router.get("/nodes", response_model=GraphNodePageResponse)
def read_graph_nodes(
    session: SessionDependency,
    filters: NodeFiltersDependency,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> GraphNodePageResponse:
    try:
        page = list_graph_nodes(session, filters=filters, limit=limit, offset=offset)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return GraphNodePageResponse.from_domain(page)


@router.get("/nodes/{node_key}/blast-radius", response_model=BlastRadiusResponse)
def read_blast_radius(
    node_key: str,
    session: SessionDependency,
    organization_id: UUID | None = None,
) -> BlastRadiusResponse:
    _validate_node_key(node_key)
    try:
        get_graph_node_detail(session, node_key)
    except GraphNodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="graph node not found") from exc
    preview = build_blast_radius_preview(
        session,
        node_key=node_key,
        organization_id=organization_id,
    )
    return BlastRadiusResponse.from_domain(preview)


@router.get("/nodes/{node_key}", response_model=GraphNodeDetailResponse)
def read_graph_node(
    node_key: str,
    session: SessionDependency,
    as_of: Annotated[str | None, Query(max_length=40)] = None,
) -> GraphNodeDetailResponse:
    _validate_node_key(node_key)
    timestamp = _parse_as_of(as_of)
    try:
        detail = get_graph_node_detail(session, node_key, as_of=timestamp)
    except GraphNodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="graph node not found") from exc
    return GraphNodeDetailResponse.from_domain(detail)


@router.get("/resolution-candidates", response_model=ResolutionCandidatePageResponse)
def read_resolution_candidates(
    session: SessionDependency,
    state: Annotated[str | None, Query(max_length=80)] = None,
    requires_review: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ResolutionCandidatePageResponse:
    try:
        page = list_resolution_candidates(
            session,
            state=state,
            requires_review=requires_review,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ResolutionCandidatePageResponse.from_domain(page)


@router.get(
    "/resolution-candidates/{candidate_id}",
    response_model=ResolutionCandidateDetailResponse,
)
def read_resolution_candidate(
    candidate_id: UUID,
    session: SessionDependency,
) -> ResolutionCandidateDetailResponse:
    try:
        detail = get_resolution_candidate_detail(session, candidate_id)
    except ResolutionCandidateNotFoundError as exc:
        raise HTTPException(status_code=404, detail="resolution candidate not found") from exc
    return ResolutionCandidateDetailResponse.from_domain(detail)


@router.post(
    "/resolution-candidates/{candidate_id}/decisions",
    response_model=ResolutionCandidateDetailResponse,
)
def decide_resolution_candidate(
    candidate_id: UUID,
    request: ResolutionDecisionRequest,
    session: SessionDependency,
) -> ResolutionCandidateDetailResponse:
    try:
        detail = get_resolution_candidate_detail(session, candidate_id)
    except ResolutionCandidateNotFoundError as exc:
        raise HTTPException(status_code=404, detail="resolution candidate not found") from exc
    organization_id = _decision_preview_organization(session, detail.candidate, request)
    preview = build_blast_radius_preview(
        session,
        node_key=detail.candidate.node_key,
        organization_id=organization_id,
    )
    decision = ResolutionDecision.create(
        candidate_id=candidate_id,
        node_key=detail.candidate.node_key,
        decision_type=request.decision_type,
        actor=request.actor,
        reason=request.reason,
        organization_id=request.organization_id,
        reverses_decision_id=request.reverses_decision_id,
        blast_radius_fingerprint=request.blast_radius_fingerprint,
    )
    try:
        record_resolution_decision(session, decision, preview=preview, now=utc_now())
    except ValueError as exc:
        status_code = 409 if "blast-radius" in str(exc) else 422
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return ResolutionCandidateDetailResponse.from_domain(
        get_resolution_candidate_detail(session, candidate_id)
    )


@router.post("/refresh", response_model=GraphRefreshResponse)
def refresh_graph(session: SessionDependency) -> GraphRefreshResponse:
    result = refresh_corporate_graph(session, now=utc_now())
    return GraphRefreshResponse(
        node_count=len(result.node_ids),
        edge_count=len(result.edge_ids),
        node_snapshot_count=result.node_snapshot_count,
        edge_snapshot_count=result.edge_snapshot_count,
        candidate_count=result.candidate_count,
    )


def _decision_preview_organization(
    session: Session,
    candidate: object,
    request: ResolutionDecisionRequest,
) -> UUID | None:
    if request.organization_id is not None:
        return request.organization_id
    if request.decision_type is ResolutionDecisionType.SPLIT:
        node_key = getattr(candidate, "node_key")
        binding = session.scalar(
            select(EntityResolutionBindingRecord).where(
                EntityResolutionBindingRecord.node_key == node_key,
                EntityResolutionBindingRecord.current.is_(True),
            )
        )
        if binding is not None:
            return binding.organization_id
    return getattr(candidate, "candidate_organization_id")


def _validate_node_key(node_key: str) -> None:
    if not node_key.strip() or len(node_key) > 500:
        raise HTTPException(status_code=422, detail="invalid graph node key")


def _parse_as_of(value: str | None):
    if value is None:
        return None
    from datetime import datetime

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="as_of must be an ISO-8601 timestamp") from exc

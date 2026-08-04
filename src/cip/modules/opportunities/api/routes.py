from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from cip.modules.opportunities.api.schemas import (
    OpportunityDetailResponse,
    OpportunityPageResponse,
    ReviewRequest,
    ReviewResponse,
    ScoreComponentOverrideRequest,
    ScoreComponentOverrideResponse,
)
from cip.modules.opportunities.domain.entities import OpportunityFamily, OpportunityState
from cip.modules.opportunities.infrastructure.errors import (
    OpportunityNotFoundError,
    ScoreComponentNotFoundError,
)
from cip.modules.opportunities.infrastructure.queries import (
    get_opportunity_detail,
    list_opportunities,
)
from cip.modules.opportunities.infrastructure.reviews import (
    override_score_component,
    review_opportunity,
)
from cip.shared.kernel.time import utc_now
from cip.shared.persistence.dependencies import get_database_session

router = APIRouter(prefix="/v1/opportunities", tags=["opportunities"])
SessionDependency = Annotated[Session, Depends(get_database_session)]


@router.get("", response_model=OpportunityPageResponse)
def list_opportunity_inbox(
    session: SessionDependency,
    state: Annotated[list[OpportunityState] | None, Query()] = None,
    family: OpportunityFamily | None = None,
    min_score: Annotated[float, Query(ge=0.0, le=100.0)] = 0.0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OpportunityPageResponse:
    page = list_opportunities(
        session,
        now=utc_now(),
        states=tuple(state or ()),
        family=family,
        min_score=min_score,
        limit=limit,
        offset=offset,
    )
    return OpportunityPageResponse.from_domain(page)


@router.get("/{opportunity_id}", response_model=OpportunityDetailResponse)
def read_opportunity(
    opportunity_id: UUID,
    session: SessionDependency,
) -> OpportunityDetailResponse:
    try:
        detail = get_opportunity_detail(session, opportunity_id)
    except OpportunityNotFoundError as exc:
        raise HTTPException(status_code=404, detail="opportunity not found") from exc
    return OpportunityDetailResponse.from_domain(detail)


@router.post("/{opportunity_id}/review", response_model=ReviewResponse)
def review_opportunity_endpoint(
    opportunity_id: UUID,
    payload: ReviewRequest,
    session: SessionDependency,
) -> ReviewResponse:
    try:
        state = review_opportunity(
            session,
            opportunity_id,
            payload.action,
            actor=payload.actor,
            now=utc_now(),
            note=payload.note,
            snoozed_until=payload.snoozed_until,
        )
    except OpportunityNotFoundError as exc:
        raise HTTPException(status_code=404, detail="opportunity not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ReviewResponse(id=opportunity_id, state=state)


@router.patch(
    "/{opportunity_id}/score-components/{component_id}",
    response_model=ScoreComponentOverrideResponse,
)
def override_score_component_endpoint(
    opportunity_id: UUID,
    component_id: UUID,
    payload: ScoreComponentOverrideRequest,
    session: SessionDependency,
) -> ScoreComponentOverrideResponse:
    try:
        score = override_score_component(
            session,
            opportunity_id,
            component_id,
            actor=payload.actor,
            now=utc_now(),
            value=payload.value,
            weight=payload.weight,
            reason=payload.reason,
        )
    except OpportunityNotFoundError as exc:
        raise HTTPException(status_code=404, detail="opportunity not found") from exc
    except ScoreComponentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="score component not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ScoreComponentOverrideResponse(
        opportunity_id=opportunity_id,
        component_id=component_id,
        score=score,
    )

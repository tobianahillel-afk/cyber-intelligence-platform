from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from cip.modules.opportunities.api.hypothesis_schemas import (
    NeedHypothesisListResponse,
    NeedHypothesisRecomputeResponse,
    NeedHypothesisResponse,
)
from cip.modules.opportunities.domain.entities import (
    HypothesisStatus,
    NeedHypothesisClass,
)
from cip.modules.opportunities.infrastructure.fusion_generation import (
    generate_need_hypotheses,
)
from cip.modules.opportunities.infrastructure.hypothesis_queries import (
    get_need_hypothesis,
    list_need_hypotheses,
)
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.service_taxonomy.domain.models import CyberServiceFamily
from cip.shared.kernel.time import utc_now
from cip.shared.persistence.dependencies import get_database_session

router = APIRouter(prefix="/v1/need-hypotheses", tags=["need-hypotheses"])
SessionDependency = Annotated[Session, Depends(get_database_session)]


@router.get("", response_model=NeedHypothesisListResponse)
def list_hypothesis_workspace(
    session: SessionDependency,
    organization_id: UUID | None = None,
    hypothesis_class: NeedHypothesisClass | None = None,
    status: HypothesisStatus | None = None,
    service_family: CyberServiceFamily | None = None,
    min_confidence: Annotated[float | None, Query(ge=0.0, le=1.0)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> NeedHypothesisListResponse:
    items = list_need_hypotheses(
        session,
        organization_id=organization_id,
        hypothesis_class=hypothesis_class.value if hypothesis_class else None,
        status=status.value if status else None,
        service_family=service_family.value if service_family else None,
        min_confidence=min_confidence,
        limit=limit,
    )
    return NeedHypothesisListResponse(
        items=tuple(NeedHypothesisResponse.from_view(item) for item in items)
    )


@router.get("/{hypothesis_id}", response_model=NeedHypothesisResponse)
def read_hypothesis(
    hypothesis_id: UUID,
    session: SessionDependency,
) -> NeedHypothesisResponse:
    view = get_need_hypothesis(session, hypothesis_id)
    if view is None:
        raise HTTPException(status_code=404, detail="need hypothesis not found")
    return NeedHypothesisResponse.from_view(view)


@router.post(
    "/organizations/{organization_id}/recompute",
    response_model=NeedHypothesisRecomputeResponse,
)
def recompute_organization_hypotheses(
    organization_id: UUID,
    session: SessionDependency,
) -> NeedHypothesisRecomputeResponse:
    if session.get(OrganizationRecord, organization_id) is None:
        raise HTTPException(status_code=404, detail="organization not found")
    hypothesis_ids = generate_need_hypotheses(
        session,
        organization_id,
        now=utc_now(),
    )
    return NeedHypothesisRecomputeResponse(
        organization_id=organization_id,
        hypothesis_ids=hypothesis_ids,
        generated_count=len(hypothesis_ids),
    )

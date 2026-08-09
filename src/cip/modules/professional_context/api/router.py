from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from cip.modules.professional_context.api.schemas import (
    OrganizationProfessionalMapResponse,
    ProfessionalPersonDetailResponse,
    ProfessionalPersonPageResponse,
)
from cip.modules.professional_context.application.view_models import ProfessionalPersonFilters
from cip.modules.professional_context.domain import (
    EmploymentState,
    LawfulBasis,
    ProfessionalReviewState,
)
from cip.modules.professional_context.infrastructure.detail_queries import (
    ProfessionalPersonNotFoundError,
    get_organization_professional_map,
    get_professional_person_detail,
)
from cip.modules.professional_context.infrastructure.queries import list_professional_people
from cip.modules.source_portfolio.api.dependencies import require_control_plane
from cip.shared.persistence.dependencies import get_database_session

router = APIRouter(
    prefix="/v1/professional-context",
    tags=["professional-context"],
    dependencies=[Depends(require_control_plane)],
)
SessionDependency = Annotated[Session, Depends(get_database_session)]


@router.get("/people", response_model=ProfessionalPersonPageResponse)
def list_people(
    session: SessionDependency,
    organization_id: UUID | None = None,
    employment_state: EmploymentState | None = None,
    review_state: ProfessionalReviewState | None = None,
    lawful_basis: LawfulBasis | None = None,
    include_suppressed: bool = False,
    include_deleted: bool = False,
    q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProfessionalPersonPageResponse:
    page = list_professional_people(
        session,
        filters=ProfessionalPersonFilters(
            organization_id=organization_id,
            employment_state=employment_state.value if employment_state else None,
            review_state=review_state.value if review_state else None,
            lawful_basis=lawful_basis.value if lawful_basis else None,
            include_suppressed=include_suppressed,
            include_deleted=include_deleted,
            query=q,
        ),
        limit=limit,
        offset=offset,
    )
    return ProfessionalPersonPageResponse.from_domain(page)


@router.get("/people/{person_key}", response_model=ProfessionalPersonDetailResponse)
def person_detail(
    person_key: str,
    session: SessionDependency,
) -> ProfessionalPersonDetailResponse:
    try:
        detail = get_professional_person_detail(session, person_key)
    except ProfessionalPersonNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="person not found",
        ) from exc
    return ProfessionalPersonDetailResponse.from_domain(detail)


@router.get(
    "/organizations/{organization_id}/map",
    response_model=OrganizationProfessionalMapResponse,
)
def organization_map(
    organization_id: UUID,
    session: SessionDependency,
) -> OrganizationProfessionalMapResponse:
    return OrganizationProfessionalMapResponse.from_domain(
        get_organization_professional_map(session, organization_id)
    )

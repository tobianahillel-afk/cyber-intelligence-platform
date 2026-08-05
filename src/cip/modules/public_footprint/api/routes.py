from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from cip.modules.public_footprint.api.schemas import (
    PublicResourceDetailResponse,
    PublicResourcePageResponse,
)
from cip.modules.public_footprint.domain.models import (
    PublicClaimType,
    PublicResourceKind,
    ResourceAccessState,
    ResourceRetrievalState,
)
from cip.modules.public_footprint.infrastructure.errors import (
    PublicResourceNotFoundError,
)
from cip.modules.public_footprint.infrastructure.queries import (
    get_public_resource_detail,
    list_public_resources,
)
from cip.modules.source_portfolio.api.dependencies import require_control_plane
from cip.shared.kernel.time import utc_now
from cip.shared.persistence.dependencies import get_database_session

router = APIRouter(
    prefix="/v1/public-footprint",
    tags=["public-footprint"],
    dependencies=[Depends(require_control_plane)],
)
SessionDependency = Annotated[Session, Depends(get_database_session)]


@router.get("/resources", response_model=PublicResourcePageResponse)
def read_public_resources(
    session: SessionDependency,
    organization_id: UUID | None = None,
    source_id: str | None = None,
    kind: PublicResourceKind | None = None,
    access_state: ResourceAccessState | None = None,
    retrieval_state: ResourceRetrievalState | None = None,
    claim_type: PublicClaimType | None = None,
    query: Annotated[str | None, Query(alias="q", max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PublicResourcePageResponse:
    try:
        page = list_public_resources(
            session,
            now=utc_now(),
            organization_id=organization_id,
            source_id=source_id,
            kind=kind,
            access_state=access_state,
            retrieval_state=retrieval_state,
            claim_type=claim_type,
            query=query,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PublicResourcePageResponse.from_domain(page)


@router.get(
    "/resources/{resource_id}",
    response_model=PublicResourceDetailResponse,
)
def read_public_resource(
    resource_id: UUID,
    session: SessionDependency,
) -> PublicResourceDetailResponse:
    try:
        detail = get_public_resource_detail(session, resource_id)
    except PublicResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="public resource not found") from exc
    return PublicResourceDetailResponse.from_domain(detail)

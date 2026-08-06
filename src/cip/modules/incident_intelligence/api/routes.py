from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from cip.modules.incident_intelligence.api.schemas import (
    IncidentDetailResponse,
    IncidentPageResponse,
)
from cip.modules.incident_intelligence.application.view_models import IncidentFilters
from cip.modules.incident_intelligence.domain.models import (
    IncidentClaimType,
    IncidentSourceKind,
    IncidentStatus,
    IncidentType,
    OrganizationLinkStatus,
)
from cip.modules.incident_intelligence.infrastructure.errors import (
    IncidentNotFoundError,
)
from cip.modules.incident_intelligence.infrastructure.queries import (
    get_incident_detail,
    list_incidents,
)
from cip.modules.source_portfolio.api.dependencies import require_control_plane
from cip.shared.persistence.dependencies import get_database_session

router = APIRouter(
    prefix="/v1/incidents",
    tags=["incidents"],
    dependencies=[Depends(require_control_plane)],
)
SessionDependency = Annotated[Session, Depends(get_database_session)]


def _incident_filters(
    status: IncidentStatus | None = None,
    incident_type: IncidentType | None = None,
    claim_type: IncidentClaimType | None = None,
    source_kind: IncidentSourceKind | None = None,
    organization_link_status: OrganizationLinkStatus | None = None,
    officially_confirmed: bool | None = None,
    historical_only: bool | None = None,
    query: Annotated[str | None, Query(alias="q", max_length=200)] = None,
) -> IncidentFilters:
    return IncidentFilters(
        status=status.value if status else None,
        incident_type=incident_type.value if incident_type else None,
        claim_type=claim_type.value if claim_type else None,
        source_kind=source_kind.value if source_kind else None,
        organization_link_status=(
            organization_link_status.value
            if organization_link_status
            else None
        ),
        officially_confirmed=officially_confirmed,
        historical_only=historical_only,
        query=query,
    )


IncidentFilterDependency = Annotated[IncidentFilters, Depends(_incident_filters)]


@router.get("", response_model=IncidentPageResponse)
def read_incidents(
    session: SessionDependency,
    filters: IncidentFilterDependency,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> IncidentPageResponse:
    try:
        page = list_incidents(
            session,
            filters=filters,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return IncidentPageResponse.from_domain(page)


@router.get("/{incident_key}", response_model=IncidentDetailResponse)
def read_incident(
    incident_key: str,
    session: SessionDependency,
) -> IncidentDetailResponse:
    if len(incident_key) > 500:
        raise HTTPException(status_code=422, detail="incident key is too long")
    try:
        detail = get_incident_detail(session, incident_key)
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="incident not found") from exc
    return IncidentDetailResponse.from_domain(detail)

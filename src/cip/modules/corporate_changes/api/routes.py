from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from cip.modules.corporate_changes.api.schemas import (
    ChangeDetailResponse,
    ChangePageResponse,
)
from cip.modules.corporate_changes.application.view_models import ChangeFilters
from cip.modules.corporate_changes.domain.models import (
    ChangeClaimType,
    ChangeEventStatus,
    ChangeEventType,
    ChangeSourceKind,
    OrganizationLinkStatus,
)
from cip.modules.corporate_changes.infrastructure.errors import (
    CorporateChangeNotFoundError,
)
from cip.modules.corporate_changes.infrastructure.queries import (
    get_change_detail,
    list_change_events,
)
from cip.modules.source_portfolio.api.dependencies import require_control_plane
from cip.shared.persistence.dependencies import get_database_session

router = APIRouter(
    prefix="/v1/corporate-changes",
    tags=["corporate-changes"],
    dependencies=[Depends(require_control_plane)],
)
SessionDependency = Annotated[Session, Depends(get_database_session)]


def _change_filters(
    status: ChangeEventStatus | None = None,
    event_type: ChangeEventType | None = None,
    claim_type: ChangeClaimType | None = None,
    source_kind: ChangeSourceKind | None = None,
    organization_link_status: OrganizationLinkStatus | None = None,
    organization_id: UUID | None = None,
    officially_confirmed: bool | None = None,
    historical_only: bool | None = None,
    query: Annotated[str | None, Query(alias="q", max_length=200)] = None,
) -> ChangeFilters:
    return ChangeFilters(
        status=status.value if status else None,
        event_type=event_type.value if event_type else None,
        claim_type=claim_type.value if claim_type else None,
        source_kind=source_kind.value if source_kind else None,
        organization_link_status=(
            organization_link_status.value if organization_link_status else None
        ),
        organization_id=organization_id,
        officially_confirmed=officially_confirmed,
        historical_only=historical_only,
        query=query,
    )


ChangeFilterDependency = Annotated[ChangeFilters, Depends(_change_filters)]


@router.get("", response_model=ChangePageResponse)
def read_change_events(
    session: SessionDependency,
    filters: ChangeFilterDependency,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ChangePageResponse:
    try:
        page = list_change_events(session, filters=filters, limit=limit, offset=offset)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ChangePageResponse.from_domain(page)


@router.get("/{event_key}", response_model=ChangeDetailResponse)
def read_change_event(
    event_key: str,
    session: SessionDependency,
) -> ChangeDetailResponse:
    if len(event_key) > 500:
        raise HTTPException(status_code=422, detail="event key is too long")
    try:
        detail = get_change_detail(session, event_key)
    except CorporateChangeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="change event not found") from exc
    return ChangeDetailResponse.from_domain(detail)

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from cip.modules.passive_exposure.api.schemas import (
    PassiveAssetDetailResponse,
    PassiveAssetPageResponse,
)
from cip.modules.passive_exposure.application.view_models import PassiveAssetFilters
from cip.modules.passive_exposure.domain.models import (
    AttributionRisk,
    OrganizationLinkStatus,
    PassiveAssetKind,
    PassiveObservationState,
)
from cip.modules.passive_exposure.infrastructure.errors import (
    PassiveAssetNotFoundError,
)
from cip.modules.passive_exposure.infrastructure.queries import (
    get_passive_asset_detail,
    list_passive_assets,
)
from cip.modules.source_portfolio.api.dependencies import require_control_plane
from cip.shared.persistence.dependencies import get_database_session

router = APIRouter(
    prefix="/v1/passive-assets",
    tags=["passive-exposure"],
    dependencies=[Depends(require_control_plane)],
)
SessionDependency = Annotated[Session, Depends(get_database_session)]


def _passive_asset_filters(
    asset_kind: PassiveAssetKind | None = None,
    state: PassiveObservationState | None = None,
    organization_link_status: OrganizationLinkStatus | None = None,
    attribution_risk: AttributionRisk | None = None,
    organization_id: UUID | None = None,
    active: bool | None = None,
    historical_only: bool | None = None,
    has_conflict: bool | None = None,
    query: Annotated[str | None, Query(alias="q", max_length=500)] = None,
) -> PassiveAssetFilters:
    return PassiveAssetFilters(
        asset_kind=asset_kind.value if asset_kind else None,
        state=state.value if state else None,
        organization_link_status=(
            organization_link_status.value if organization_link_status else None
        ),
        attribution_risk=attribution_risk.value if attribution_risk else None,
        organization_id=organization_id,
        active=active,
        historical_only=historical_only,
        has_conflict=has_conflict,
        query=query,
    )


PassiveAssetFilterDependency = Annotated[
    PassiveAssetFilters,
    Depends(_passive_asset_filters),
]


@router.get("", response_model=PassiveAssetPageResponse)
def read_passive_assets(
    session: SessionDependency,
    filters: PassiveAssetFilterDependency,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PassiveAssetPageResponse:
    try:
        page = list_passive_assets(
            session,
            filters=filters,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PassiveAssetPageResponse.from_domain(page)


@router.get("/{asset_id}", response_model=PassiveAssetDetailResponse)
def read_passive_asset(
    asset_id: UUID,
    session: SessionDependency,
) -> PassiveAssetDetailResponse:
    try:
        detail = get_passive_asset_detail(session, asset_id)
    except PassiveAssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="passive asset not found") from exc
    return PassiveAssetDetailResponse.from_domain(detail)

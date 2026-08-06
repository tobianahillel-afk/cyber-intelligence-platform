from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from cip.modules.source_portfolio.api.dependencies import require_control_plane
from cip.modules.threat_telemetry.api.schemas import (
    IndicatorDetailResponse,
    IndicatorPageResponse,
)
from cip.modules.threat_telemetry.application.view_models import IndicatorFilters
from cip.modules.threat_telemetry.domain.models import (
    IndicatorState,
    IndicatorType,
    SensorScope,
    TelemetrySourceKind,
)
from cip.modules.threat_telemetry.infrastructure.errors import (
    ThreatIndicatorNotFoundError,
)
from cip.modules.threat_telemetry.infrastructure.queries import (
    get_threat_indicator_detail,
    list_threat_indicators,
)
from cip.shared.persistence.dependencies import get_database_session

router = APIRouter(
    prefix="/v1/threat-indicators",
    tags=["threat-telemetry"],
    dependencies=[Depends(require_control_plane)],
)
SessionDependency = Annotated[Session, Depends(get_database_session)]


def _indicator_filters(
    indicator_type: IndicatorType | None = None,
    state: IndicatorState | None = None,
    source_kind: TelemetrySourceKind | None = None,
    sensor_scope: SensorScope | None = None,
    active: bool | None = None,
    shared_infrastructure: bool | None = None,
    historical_only: bool | None = None,
    has_conflict: bool | None = None,
    query: Annotated[str | None, Query(alias="q", max_length=500)] = None,
) -> IndicatorFilters:
    return IndicatorFilters(
        indicator_type=indicator_type.value if indicator_type else None,
        state=state.value if state else None,
        source_kind=source_kind.value if source_kind else None,
        sensor_scope=sensor_scope.value if sensor_scope else None,
        active=active,
        shared_infrastructure=shared_infrastructure,
        historical_only=historical_only,
        has_conflict=has_conflict,
        query=query,
    )


IndicatorFilterDependency = Annotated[IndicatorFilters, Depends(_indicator_filters)]


@router.get("", response_model=IndicatorPageResponse)
def read_threat_indicators(
    session: SessionDependency,
    filters: IndicatorFilterDependency,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> IndicatorPageResponse:
    try:
        page = list_threat_indicators(
            session,
            filters=filters,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return IndicatorPageResponse.from_domain(page)


@router.get("/{indicator_id}", response_model=IndicatorDetailResponse)
def read_threat_indicator(
    indicator_id: UUID,
    session: SessionDependency,
) -> IndicatorDetailResponse:
    try:
        detail = get_threat_indicator_detail(session, indicator_id)
    except ThreatIndicatorNotFoundError as exc:
        raise HTTPException(status_code=404, detail="threat indicator not found") from exc
    return IndicatorDetailResponse.from_domain(detail)

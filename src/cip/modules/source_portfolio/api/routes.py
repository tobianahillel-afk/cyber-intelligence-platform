from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from cip.modules.source_portfolio.api.dependencies import (
    ensure_source_portfolio,
    require_control_plane,
)
from cip.modules.source_portfolio.api.schemas import (
    ActorRequest,
    BackfillRequest,
    BackfillResponse,
    PriorityRefreshResponse,
    SourcePortfolioPageResponse,
    SourcePortfolioResponse,
)
from cip.modules.source_portfolio.application.service import (
    SourcePortfolioNotFoundError,
    SourcePortfolioStateError,
    cancel_backfill,
    disable_source,
    get_source_health,
    get_source_portfolio,
    list_source_portfolio,
    pause_source,
    refresh_freshness,
    request_backfill,
    request_priority_refresh,
    resume_source,
)
from cip.shared.config.settings import Settings, get_settings
from cip.shared.kernel.time import utc_now
from cip.shared.persistence.dependencies import get_database_session

router = APIRouter(
    prefix="/v1/source-portfolio",
    tags=["source-portfolio"],
    dependencies=[Depends(require_control_plane)],
)
SessionDependency = Annotated[Session, Depends(get_database_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


@router.get("/sources", response_model=SourcePortfolioPageResponse)
def read_source_portfolio(
    session: SessionDependency,
    settings: SettingsDependency,
) -> SourcePortfolioPageResponse:
    _prepare(session, settings)
    items = [
        SourcePortfolioResponse.from_domain(entry, get_source_health(session, entry.source_id))
        for entry in list_source_portfolio(session)
    ]
    return SourcePortfolioPageResponse(items=items, total=len(items))


@router.get("/sources/{source_id}", response_model=SourcePortfolioResponse)
def read_source(
    source_id: str,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SourcePortfolioResponse:
    _prepare(session, settings)
    return _response(session, source_id)


@router.post("/sources/{source_id}/backfills", response_model=BackfillResponse)
def create_backfill(
    source_id: str,
    payload: BackfillRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> BackfillResponse:
    _prepare(session, settings)
    try:
        partition_ids = request_backfill(
            session,
            source_id,
            [(item.lower_bound, item.upper_bound) for item in payload.partitions],
            actor=payload.actor,
            now=utc_now(),
        )
    except SourcePortfolioNotFoundError as exc:
        raise HTTPException(status_code=404, detail="source not found") from exc
    except SourcePortfolioStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return BackfillResponse(partition_ids=list(partition_ids))


@router.post("/sources/{source_id}/backfills/cancel", response_model=SourcePortfolioResponse)
def cancel_source_backfill(
    source_id: str,
    payload: ActorRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SourcePortfolioResponse:
    _prepare(session, settings)
    try:
        cancel_backfill(
            session,
            source_id,
            actor=payload.actor,
            now=utc_now(),
        )
    except SourcePortfolioNotFoundError as exc:
        raise HTTPException(status_code=404, detail="source not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _response(session, source_id)


@router.post(
    "/sources/{source_id}/priority-refresh",
    response_model=PriorityRefreshResponse,
)
def create_priority_refresh(
    source_id: str,
    payload: ActorRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> PriorityRefreshResponse:
    _prepare(session, settings)
    try:
        result = request_priority_refresh(
            session,
            source_id,
            actor=payload.actor,
            now=utc_now(),
        )
    except SourcePortfolioNotFoundError as exc:
        raise HTTPException(status_code=404, detail="source not found") from exc
    except SourcePortfolioStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PriorityRefreshResponse(job_id=result.job_id, created=result.created)


@router.post("/sources/{source_id}/pause", response_model=SourcePortfolioResponse)
def pause_source_route(
    source_id: str,
    payload: ActorRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SourcePortfolioResponse:
    _prepare(session, settings)
    return _change_status(session, source_id, payload.actor, "pause")


@router.post("/sources/{source_id}/resume", response_model=SourcePortfolioResponse)
def resume_source_route(
    source_id: str,
    payload: ActorRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SourcePortfolioResponse:
    _prepare(session, settings)
    return _change_status(session, source_id, payload.actor, "resume")


@router.post("/sources/{source_id}/disable", response_model=SourcePortfolioResponse)
def disable_source_route(
    source_id: str,
    payload: ActorRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SourcePortfolioResponse:
    _prepare(session, settings)
    return _change_status(session, source_id, payload.actor, "disable")


@router.post("/sources/{source_id}/refresh-freshness", response_model=SourcePortfolioResponse)
def refresh_source_freshness(
    source_id: str,
    payload: ActorRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SourcePortfolioResponse:
    del payload
    _prepare(session, settings)
    try:
        refresh_freshness(session, source_id, now=utc_now())
    except SourcePortfolioNotFoundError as exc:
        raise HTTPException(status_code=404, detail="source not found") from exc
    return _response(session, source_id)


def _prepare(session: Session, settings: Settings) -> None:
    ensure_source_portfolio(session, settings)


def _response(session: Session, source_id: str) -> SourcePortfolioResponse:
    try:
        entry = get_source_portfolio(session, source_id)
        health = get_source_health(session, source_id)
    except SourcePortfolioNotFoundError as exc:
        raise HTTPException(status_code=404, detail="source not found") from exc
    return SourcePortfolioResponse.from_domain(entry, health)


def _change_status(
    session: Session,
    source_id: str,
    actor: str,
    action: Literal["pause", "resume", "disable"],
) -> SourcePortfolioResponse:
    try:
        if action == "pause":
            pause_source(session, source_id, actor=actor, now=utc_now())
        elif action == "resume":
            resume_source(session, source_id, actor=actor, now=utc_now())
        else:
            disable_source(session, source_id, actor=actor, now=utc_now())
    except SourcePortfolioNotFoundError as exc:
        raise HTTPException(status_code=404, detail="source not found") from exc
    except SourcePortfolioStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _response(session, source_id)

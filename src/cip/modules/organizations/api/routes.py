from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from cip.modules.organizations.api.schemas import (
    IdentityResponse,
    MergeCandidatePageResponse,
    MergeCandidateResponse,
    MergeCandidateReviewRequest,
    MergeCandidateReviewResponse,
)
from cip.modules.organizations.domain.identity import MatchState
from cip.modules.organizations.infrastructure.identity_persistence import (
    IdentityReviewConflictError,
    review_merge_candidate,
)
from cip.modules.organizations.infrastructure.identity_queries import (
    MergeCandidateNotFoundError,
    OrganizationIdentityNotFoundError,
    OrganizationNotFoundError,
    get_merge_candidate,
    get_organization_identity,
    list_merge_candidates,
    list_organization_identities,
)
from cip.shared.kernel.time import utc_now
from cip.shared.persistence.dependencies import get_database_session

router = APIRouter(prefix="/v1/organizations", tags=["organization-identity"])
SessionDependency = Annotated[Session, Depends(get_database_session)]


@router.get("/{organization_id}/identities", response_model=list[IdentityResponse])
def read_organization_identities(
    organization_id: UUID,
    session: SessionDependency,
) -> list[IdentityResponse]:
    try:
        identities = list_organization_identities(session, organization_id)
    except OrganizationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="organization not found") from exc
    return [IdentityResponse.from_domain(identity) for identity in identities]


@router.get("/identities/{identity_id}", response_model=IdentityResponse)
def read_identity(
    identity_id: UUID,
    session: SessionDependency,
) -> IdentityResponse:
    try:
        identity = get_organization_identity(session, identity_id)
    except OrganizationIdentityNotFoundError as exc:
        raise HTTPException(status_code=404, detail="organization identity not found") from exc
    return IdentityResponse.from_domain(identity)


@router.get("/identity-merge-candidates", response_model=MergeCandidatePageResponse)
def read_merge_candidates(
    session: SessionDependency,
    state: Annotated[list[MatchState] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MergeCandidatePageResponse:
    page = list_merge_candidates(
        session,
        states=tuple(state or ()),
        limit=limit,
        offset=offset,
    )
    return MergeCandidatePageResponse.from_domain(page)


@router.get(
    "/identity-merge-candidates/{candidate_id}",
    response_model=MergeCandidateResponse,
)
def read_merge_candidate(
    candidate_id: UUID,
    session: SessionDependency,
) -> MergeCandidateResponse:
    try:
        candidate = get_merge_candidate(session, candidate_id)
    except MergeCandidateNotFoundError as exc:
        raise HTTPException(status_code=404, detail="merge candidate not found") from exc
    return MergeCandidateResponse.from_domain(candidate)


@router.post(
    "/identity-merge-candidates/{candidate_id}/review",
    response_model=MergeCandidateReviewResponse,
)
def review_merge_candidate_endpoint(
    candidate_id: UUID,
    payload: MergeCandidateReviewRequest,
    session: SessionDependency,
) -> MergeCandidateReviewResponse:
    try:
        candidate = review_merge_candidate(
            session,
            candidate_id,
            confirm=payload.action == "confirm",
            actor=payload.actor,
            reviewed_at=utc_now(),
            note=payload.note,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="merge candidate not found") from exc
    except IdentityReviewConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return MergeCandidateReviewResponse(id=candidate.id, state=MatchState(candidate.state))

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from cip.modules.relationship_intelligence.api.schemas import (
    RelationshipDetailResponse,
    RelationshipPageResponse,
)
from cip.modules.relationship_intelligence.application.view_models import RelationshipFilters
from cip.modules.relationship_intelligence.domain.models import (
    RelationshipEvidenceClass,
    RelationshipOrganizationLinkStatus,
    RelationshipRole,
    RelationshipSourceKind,
    RelationshipStatus,
)
from cip.modules.relationship_intelligence.infrastructure.errors import (
    RelationshipNotFoundError,
)
from cip.modules.relationship_intelligence.infrastructure.queries import (
    get_relationship_detail,
    list_relationships,
)
from cip.modules.source_portfolio.api.dependencies import require_control_plane
from cip.shared.persistence.dependencies import get_database_session

router = APIRouter(
    prefix="/v1/relationships",
    tags=["relationships"],
    dependencies=[Depends(require_control_plane)],
)
SessionDependency = Annotated[Session, Depends(get_database_session)]


def _evidence_filters(
    status: RelationshipStatus | None = None,
    role: RelationshipRole | None = None,
    evidence_class: RelationshipEvidenceClass | None = None,
    source_kind: RelationshipSourceKind | None = None,
) -> RelationshipFilters:
    return RelationshipFilters(
        status=status.value if status else None,
        role=role.value if role else None,
        evidence_class=evidence_class.value if evidence_class else None,
        source_kind=source_kind.value if source_kind else None,
    )


EvidenceFiltersDependency = Annotated[RelationshipFilters, Depends(_evidence_filters)]


def _identity_filters(
    source_link_status: RelationshipOrganizationLinkStatus | None = None,
    target_link_status: RelationshipOrganizationLinkStatus | None = None,
    organization_id: UUID | None = None,
) -> RelationshipFilters:
    return RelationshipFilters(
        source_link_status=source_link_status.value if source_link_status else None,
        target_link_status=target_link_status.value if target_link_status else None,
        organization_id=organization_id,
    )


IdentityFiltersDependency = Annotated[RelationshipFilters, Depends(_identity_filters)]


def _context_filters(
    contract_backed_current: bool | None = None,
    historical_only: bool | None = None,
    query: Annotated[str | None, Query(alias="q", max_length=200)] = None,
) -> RelationshipFilters:
    return RelationshipFilters(
        contract_backed_current=contract_backed_current,
        historical_only=historical_only,
        query=query,
    )


ContextFiltersDependency = Annotated[RelationshipFilters, Depends(_context_filters)]


def _relationship_filters(
    evidence: EvidenceFiltersDependency,
    identity: IdentityFiltersDependency,
    context: ContextFiltersDependency,
) -> RelationshipFilters:
    return RelationshipFilters(
        status=evidence.status,
        role=evidence.role,
        evidence_class=evidence.evidence_class,
        source_kind=evidence.source_kind,
        source_link_status=identity.source_link_status,
        target_link_status=identity.target_link_status,
        organization_id=identity.organization_id,
        contract_backed_current=context.contract_backed_current,
        historical_only=context.historical_only,
        query=context.query,
    )


RelationshipFilterDependency = Annotated[RelationshipFilters, Depends(_relationship_filters)]


@router.get("", response_model=RelationshipPageResponse)
def read_relationships(
    session: SessionDependency,
    filters: RelationshipFilterDependency,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RelationshipPageResponse:
    try:
        page = list_relationships(session, filters=filters, limit=limit, offset=offset)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RelationshipPageResponse.from_domain(page)


@router.get("/{relationship_key}", response_model=RelationshipDetailResponse)
def read_relationship(
    relationship_key: str,
    session: SessionDependency,
) -> RelationshipDetailResponse:
    if len(relationship_key) > 500:
        raise HTTPException(status_code=422, detail="relationship key is too long")
    try:
        detail = get_relationship_detail(session, relationship_key)
    except RelationshipNotFoundError as exc:
        raise HTTPException(status_code=404, detail="relationship not found") from exc
    return RelationshipDetailResponse.from_domain(detail)

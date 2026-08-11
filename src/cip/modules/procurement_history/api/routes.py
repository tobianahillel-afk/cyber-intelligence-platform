from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from cip.modules.procurement_history.api.schemas import (
    ProcurementContractDetailResponse,
    ProcurementContractPageResponse,
)
from cip.modules.procurement_history.domain.models import ContractStatus
from cip.modules.procurement_history.infrastructure.errors import (
    ProcurementContractNotFoundError,
)
from cip.modules.procurement_history.infrastructure.queries import (
    get_procurement_contract_detail,
    list_procurement_contracts,
)
from cip.modules.service_taxonomy.domain.models import parse_service_family
from cip.modules.source_portfolio.api.dependencies import require_control_plane
from cip.shared.kernel.time import utc_now
from cip.shared.persistence.dependencies import get_database_session

router = APIRouter(
    prefix="/v1/procurement-history",
    tags=["procurement-history"],
    dependencies=[Depends(require_control_plane)],
)
SessionDependency = Annotated[Session, Depends(get_database_session)]


@router.get("/contracts", response_model=ProcurementContractPageResponse)
def read_procurement_contracts(
    session: SessionDependency,
    status: Annotated[list[ContractStatus] | None, Query()] = None,
    family: str | None = None,
    buyer_organization_id: UUID | None = None,
    renewal_from: date | None = None,
    renewal_to: date | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProcurementContractPageResponse:
    try:
        parsed_family = parse_service_family(family) if family is not None else None
        page = list_procurement_contracts(
            session,
            now=utc_now(),
            statuses=tuple(status or ()),
            family=parsed_family,
            buyer_organization_id=buyer_organization_id,
            renewal_from=renewal_from,
            renewal_to=renewal_to,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ProcurementContractPageResponse.from_domain(page)


@router.get(
    "/contracts/{contract_id}",
    response_model=ProcurementContractDetailResponse,
)
def read_procurement_contract(
    contract_id: UUID,
    session: SessionDependency,
) -> ProcurementContractDetailResponse:
    try:
        detail = get_procurement_contract_detail(session, contract_id)
    except ProcurementContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail="procurement contract not found") from exc
    return ProcurementContractDetailResponse.from_domain(detail)

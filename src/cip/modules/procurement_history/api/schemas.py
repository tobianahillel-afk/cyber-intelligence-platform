from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from cip.modules.procurement_history.application.view_models import (
    ProcurementContractDetail,
    ProcurementContractPage,
)


class ProcurementContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    procedure_id: UUID
    buyer_organization_id: UUID
    buyer_name: str
    title: str
    status: str
    amount_value: Decimal | None
    amount_upper_value: Decimal | None
    currency: str | None
    amount_type: str | None
    award_date: date | None
    conclusion_date: date | None
    conclusion_date_basis: str
    notification_date: date | None
    notification_date_basis: str
    start_date: date | None
    start_date_basis: str
    end_date: date | None
    end_date_basis: str
    renewal_date: date | None
    renewal_date_basis: str
    confidence: float
    provider_names: tuple[str, ...]
    service_families: tuple[str, ...]
    source_ids: tuple[str, ...]
    updated_at: datetime


class ProcurementContractPageResponse(BaseModel):
    items: tuple[ProcurementContractResponse, ...]
    total: int
    limit: int
    offset: int
    generated_at: datetime

    @classmethod
    def from_domain(cls, page: ProcurementContractPage) -> Self:
        return cls(
            items=tuple(
                ProcurementContractResponse.model_validate(item) for item in page.items
            ),
            total=page.total,
            limit=page.limit,
            offset=page.offset,
            generated_at=page.generated_at,
        )


class ProcurementPartyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    published_name: str
    resolution_status: str
    confidence: float
    organization_id: UUID | None
    official_identifier: str | None


class ProcurementServiceFamilyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    family: str
    matched_terms: tuple[str, ...]
    confidence: float


class ProcurementPublicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: str
    source_record_key: str
    kind: str
    procedure_status: str
    title: str
    source_url: str
    published_at: datetime | None
    collected_at: datetime
    details: dict[str, object]


class ProcurementContractDetailResponse(BaseModel):
    contract: ProcurementContractResponse
    contract_key: str
    procedure_key: str
    procedure_title: str
    procedure_status: str
    first_published_at: datetime | None
    latest_published_at: datetime | None
    parties: tuple[ProcurementPartyResponse, ...]
    service_classifications: tuple[ProcurementServiceFamilyResponse, ...]
    publications: tuple[ProcurementPublicationResponse, ...]

    @classmethod
    def from_domain(cls, detail: ProcurementContractDetail) -> Self:
        return cls(
            contract=ProcurementContractResponse.model_validate(detail.contract),
            contract_key=detail.contract_key,
            procedure_key=detail.procedure_key,
            procedure_title=detail.procedure_title,
            procedure_status=detail.procedure_status,
            first_published_at=detail.first_published_at,
            latest_published_at=detail.latest_published_at,
            parties=tuple(
                ProcurementPartyResponse.model_validate(item) for item in detail.parties
            ),
            service_classifications=tuple(
                ProcurementServiceFamilyResponse.model_validate(item)
                for item in detail.service_classifications
            ),
            publications=tuple(
                ProcurementPublicationResponse.model_validate(item)
                for item in detail.publications
            ),
        )

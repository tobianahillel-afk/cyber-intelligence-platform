from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProcurementPartyItem:
    role: str
    published_name: str
    resolution_status: str
    confidence: float
    organization_id: UUID | None
    official_identifier: str | None


@dataclass(frozen=True, slots=True)
class ProcurementServiceFamilyItem:
    family: str
    matched_terms: tuple[str, ...]
    confidence: float


@dataclass(frozen=True, slots=True)
class ProcurementPublicationItem:
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


@dataclass(frozen=True, slots=True)
class ProcurementContractListItem:
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


@dataclass(frozen=True, slots=True)
class ProcurementContractPage:
    items: tuple[ProcurementContractListItem, ...]
    total: int
    limit: int
    offset: int
    generated_at: datetime


@dataclass(frozen=True, slots=True)
class ProcurementContractDetail:
    contract: ProcurementContractListItem
    contract_key: str
    procedure_key: str
    procedure_title: str
    procedure_status: str
    first_published_at: datetime | None
    latest_published_at: datetime | None
    parties: tuple[ProcurementPartyItem, ...]
    service_classifications: tuple[ProcurementServiceFamilyItem, ...]
    publications: tuple[ProcurementPublicationItem, ...]

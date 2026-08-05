from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from types import MappingProxyType
from typing import Mapping
from uuid import UUID, uuid4

from cip.modules.service_taxonomy.domain.models import ServiceFamilyMatch
from cip.shared.kernel.time import require_aware_utc


class ProcurementPublicationKind(StrEnum):
    NOTICE = "notice"
    RECTIFICATION = "rectification"
    RESULT = "result"
    AWARD = "award"
    AMENDMENT = "amendment"
    CANCELLATION = "cancellation"
    UNKNOWN = "unknown"


class ProcurementProcedureStatus(StrEnum):
    OPEN = "open"
    AWARDED = "awarded"
    CANCELLED = "cancelled"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class ContractStatus(StrEnum):
    AWARDED = "awarded"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class DateBasis(StrEnum):
    PUBLISHED = "published"
    DERIVED = "derived"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"


class ProcurementPartyRole(StrEnum):
    BUYER = "buyer"
    AWARDEE = "awardee"
    CONSORTIUM_MEMBER = "consortium_member"
    SUBCONTRACTOR = "subcontractor"


class PartyResolutionStatus(StrEnum):
    CONFIRMED = "confirmed"
    CANDIDATE = "candidate"
    UNRESOLVED = "unresolved"


class AmountType(StrEnum):
    EXACT = "exact"
    ESTIMATED = "estimated"
    MAXIMUM = "maximum"
    RANGE = "range"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MoneyAmount:
    value: Decimal
    currency: str
    amount_type: AmountType = AmountType.EXACT
    upper_value: Decimal | None = None

    def __post_init__(self) -> None:
        value = Decimal(self.value)
        upper = Decimal(self.upper_value) if self.upper_value is not None else None
        currency = self.currency.strip().upper()
        if value < 0:
            raise ValueError("amount value cannot be negative")
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("currency must be an ISO 4217 alpha-3 code")
        if self.amount_type is AmountType.RANGE:
            if upper is None or upper < value:
                raise ValueError("range amount requires upper_value >= value")
        elif upper is not None:
            raise ValueError("upper_value is allowed only for range amounts")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "upper_value", upper)
        object.__setattr__(self, "currency", currency)


@dataclass(frozen=True, slots=True)
class ProcurementParty:
    role: ProcurementPartyRole
    published_name: str
    resolution_status: PartyResolutionStatus
    confidence: float
    organization_id: UUID | None = None
    official_identifier: str | None = None

    def __post_init__(self) -> None:
        name = self.published_name.strip()
        identifier = _optional_text(self.official_identifier)
        if not name:
            raise ValueError("published party name is required")
        if len(name) > 500:
            raise ValueError("published party name cannot exceed 500 characters")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("party confidence must be between 0 and 1")
        if self.resolution_status is PartyResolutionStatus.CONFIRMED:
            if self.organization_id is None:
                raise ValueError("confirmed party requires organization_id")
        object.__setattr__(self, "published_name", name)
        object.__setattr__(self, "official_identifier", identifier)

    @property
    def identity_key(self) -> str:
        organization = str(self.organization_id) if self.organization_id else "unresolved"
        material = (
            f"{self.role.value}\0{organization}\0"
            f"{' '.join(self.published_name.casefold().split())}"
        )
        return sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ProcurementPublication:
    procedure_key: str
    source_id: str
    source_record_key: str
    source_url: str
    kind: ProcurementPublicationKind
    procedure_status: ProcurementProcedureStatus
    buyer_organization_id: UUID
    title: str
    content_hash_sha256: str
    collected_at: datetime
    id: UUID = field(default_factory=uuid4)
    published_at: datetime | None = None
    evidence_id: UUID | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("procedure_key", "source_id", "source_record_key", "source_url"):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} is required")
            object.__setattr__(self, field_name, value)
        title = self.title.strip()
        if not title:
            raise ValueError("publication title is required")
        if len(title) > 4_000:
            raise ValueError("publication title cannot exceed 4000 characters")
        content_hash = self.content_hash_sha256.strip().lower()
        if len(content_hash) != 64 or any(char not in "0123456789abcdef" for char in content_hash):
            raise ValueError("content_hash_sha256 must be a lowercase SHA-256 digest")
        collected = require_aware_utc(self.collected_at, field_name="collected_at")
        published = self.published_at
        if published is not None:
            published = require_aware_utc(published, field_name="published_at")
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "content_hash_sha256", content_hash)
        object.__setattr__(self, "collected_at", collected)
        object.__setattr__(self, "published_at", published)
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))

    @property
    def revision_key(self) -> str:
        material = (
            f"{self.source_id}\0{self.source_record_key}\0{self.content_hash_sha256}"
        )
        return sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ProcurementContractProjection:
    contract_key: str
    procedure_key: str
    buyer_organization_id: UUID
    title: str
    status: ContractStatus
    confidence: float
    parties: tuple[ProcurementParty, ...] = ()
    service_families: tuple[ServiceFamilyMatch, ...] = ()
    amount: MoneyAmount | None = None
    award_date: date | None = None
    start_date: date | None = None
    start_date_basis: DateBasis = DateBasis.UNKNOWN
    end_date: date | None = None
    end_date_basis: DateBasis = DateBasis.UNKNOWN
    renewal_date: date | None = None
    renewal_date_basis: DateBasis = DateBasis.UNKNOWN

    def __post_init__(self) -> None:
        contract_key = self.contract_key.strip()
        procedure_key = self.procedure_key.strip()
        title = self.title.strip()
        if not contract_key or not procedure_key or not title:
            raise ValueError("contract_key, procedure_key, and title are required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("contract confidence must be between 0 and 1")
        _validate_date_basis(self.start_date, self.start_date_basis, "start_date")
        _validate_date_basis(self.end_date, self.end_date_basis, "end_date")
        _validate_date_basis(self.renewal_date, self.renewal_date_basis, "renewal_date")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot precede start_date")
        if self.renewal_date and self.end_date and self.renewal_date < self.end_date:
            raise ValueError("renewal_date cannot precede end_date")
        object.__setattr__(self, "contract_key", contract_key)
        object.__setattr__(self, "procedure_key", procedure_key)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "parties", _unique_parties(self.parties))
        object.__setattr__(self, "service_families", _unique_families(self.service_families))


@dataclass(frozen=True, slots=True)
class ProcurementHistoryProjection:
    publication: ProcurementPublication
    contract: ProcurementContractProjection | None = None

    def __post_init__(self) -> None:
        if self.contract is None:
            return
        if self.contract.procedure_key != self.publication.procedure_key:
            raise ValueError("contract procedure must match publication procedure")
        if self.contract.buyer_organization_id != self.publication.buyer_organization_id:
            raise ValueError("contract buyer must match publication buyer")
        if self.publication.kind not in {
            ProcurementPublicationKind.RESULT,
            ProcurementPublicationKind.AWARD,
            ProcurementPublicationKind.AMENDMENT,
            ProcurementPublicationKind.CANCELLATION,
        }:
            raise ValueError("a contract projection requires a contract lifecycle publication")


def _validate_date_basis(value: date | None, basis: DateBasis, field_name: str) -> None:
    if value is None and basis is not DateBasis.UNKNOWN:
        raise ValueError(f"{field_name} basis must be unknown when date is absent")
    if value is not None and basis is DateBasis.UNKNOWN:
        raise ValueError(f"{field_name} basis is required when date is present")


def _unique_parties(parties: tuple[ProcurementParty, ...]) -> tuple[ProcurementParty, ...]:
    unique: dict[str, ProcurementParty] = {}
    for party in parties:
        unique[party.identity_key] = party
    return tuple(unique.values())


def _unique_families(
    families: tuple[ServiceFamilyMatch, ...],
) -> tuple[ServiceFamilyMatch, ...]:
    unique = {match.family: match for match in families}
    return tuple(unique[family] for family in sorted(unique, key=lambda value: value.value))


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None

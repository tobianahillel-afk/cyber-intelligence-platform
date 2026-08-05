from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cip.adapters.sources.procurement_signals import matched_procurement_terms
from cip.adapters.sources.ted_search.schemas import TedNotice
from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.evidence.domain.entities import Evidence
from cip.modules.opportunities.domain.entities import CommercialSignal, SignalType
from cip.modules.organizations.domain.entities import Organization
from cip.modules.procurement_history.domain.models import (
    ContractStatus,
    DateBasis,
    MoneyAmount,
    PartyResolutionStatus,
    ProcurementContractProjection,
    ProcurementHistoryProjection,
    ProcurementParty,
    ProcurementPartyRole,
    ProcurementProcedureStatus,
    ProcurementPublication,
    ProcurementPublicationKind,
)
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.service_taxonomy.domain.classifier import classify_service_families
from cip.modules.source_governance.domain.models import DataCategory
from cip.shared.kernel.time import require_aware_utc

ADAPTER_ID = "ted-search-api"
ADAPTER_VERSION = "1.1.0"
SOURCE_ID = "ted-search"
COUNTRY_CODES = {
    "AUT": "AT",
    "BEL": "BE",
    "BGR": "BG",
    "CHE": "CH",
    "CYP": "CY",
    "CZE": "CZ",
    "DEU": "DE",
    "DNK": "DK",
    "ESP": "ES",
    "EST": "EE",
    "FIN": "FI",
    "FRA": "FR",
    "GRC": "GR",
    "HRV": "HR",
    "HUN": "HU",
    "IRL": "IE",
    "ISL": "IS",
    "ITA": "IT",
    "LTU": "LT",
    "LUX": "LU",
    "LVA": "LV",
    "MLT": "MT",
    "NLD": "NL",
    "NOR": "NO",
    "POL": "PL",
    "PRT": "PT",
    "ROU": "RO",
    "SVK": "SK",
    "SVN": "SI",
    "SWE": "SE",
}


@dataclass(frozen=True, slots=True)
class TedMapping:
    observation: RawObservation
    buyer: Organization
    procurement: ProcurementHistoryProjection
    projection: CommercialProjection | None


def map_ted_notice(
    notice: TedNotice,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> TedMapping | None:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    title = notice.title()
    matched_terms = matched_procurement_terms(title)
    if not matched_terms:
        return None
    buyer = _buyer(notice, collected_at=collected)
    notice_url = f"https://ted.europa.eu/en/notice/{notice.publication_number}/html"
    payload_hash = _payload_hash(notice)
    published_at = _aware(notice.publication_timestamp())
    deadline = _aware(notice.deadline_timestamp())
    usable_deadline = deadline if deadline is not None and deadline > collected else None
    kind = _publication_kind(notice)
    procurement = _procurement_projection(
        notice,
        buyer=buyer,
        kind=kind,
        notice_url=notice_url,
        payload_hash=payload_hash,
        published_at=published_at,
        collected_at=collected,
    )
    observation = RawObservation(
        source_id=SOURCE_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        collection_job_id=collection_job_id,
        source_record_type=_record_type(kind),
        source_record_key=notice.publication_number,
        source_url=notice_url,
        payload_hash_sha256=payload_hash,
        data_categories=frozenset({DataCategory.PUBLIC_TENDER}),
        collected_at=collected,
        published_at=published_at,
        schema_fingerprint="ted-search-v3-selected-fields-2",
        classification="internal",
        retention_until=retention_until,
    )
    projection = None
    if _is_actionable(kind, deadline=deadline, collected_at=collected):
        projection = _commercial_projection(
            notice,
            buyer=buyer,
            matched_terms=matched_terms,
            notice_url=notice_url,
            payload_hash=payload_hash,
            published_at=published_at,
            deadline=usable_deadline,
            collected_at=collected,
            retention_until=retention_until,
        )
    return TedMapping(observation, buyer, procurement, projection)


def _procurement_projection(
    notice: TedNotice,
    *,
    buyer: Organization,
    kind: ProcurementPublicationKind,
    notice_url: str,
    payload_hash: str,
    published_at: datetime | None,
    collected_at: datetime,
) -> ProcurementHistoryProjection:
    procedure_identifier = notice.procedure_id() or notice.publication_number
    procedure_key = f"ted:procedure:{procedure_identifier}"
    publication = ProcurementPublication(
        id=uuid5(
            NAMESPACE_URL,
            f"ted:publication:{notice.publication_number}:{payload_hash}",
        ),
        procedure_key=procedure_key,
        source_id=SOURCE_ID,
        source_record_key=notice.publication_number,
        source_url=notice_url,
        kind=kind,
        procedure_status=_procedure_status(kind),
        buyer_organization_id=buyer.id,
        title=notice.title(),
        content_hash_sha256=payload_hash,
        collected_at=collected_at,
        published_at=published_at,
        details={
            "procedure_identifier": procedure_identifier,
            "contract_identifiers": list(notice.contract_ids()),
            "notice_types": list(notice.notice_types()),
            "winner_names": list(notice.winner_names()),
            "winner_identifiers": list(notice.winner_identifiers()),
            "tender_values": list(notice.tender_values()),
            "tender_currencies": list(notice.tender_currencies()),
        },
    )
    contract = _contract_projection(
        notice,
        buyer=buyer,
        kind=kind,
        procedure_key=procedure_key,
        published_at=published_at,
    )
    return ProcurementHistoryProjection(publication=publication, contract=contract)


def _contract_projection(
    notice: TedNotice,
    *,
    buyer: Organization,
    kind: ProcurementPublicationKind,
    procedure_key: str,
    published_at: datetime | None,
) -> ProcurementContractProjection | None:
    winner_names = notice.winner_names()
    contract_ids = notice.contract_ids()
    conclusion_at = _aware(notice.conclusion_timestamp())
    if not winner_names and not contract_ids and conclusion_at is None:
        return None
    if kind not in {
        ProcurementPublicationKind.AWARD,
        ProcurementPublicationKind.AMENDMENT,
        ProcurementPublicationKind.CANCELLATION,
    }:
        return None
    winner_identifiers = notice.winner_identifiers()
    parties = tuple(
        ProcurementParty(
            role=ProcurementPartyRole.AWARDEE,
            published_name=name,
            resolution_status=PartyResolutionStatus.UNRESOLVED,
            confidence=0.72,
            official_identifier=(
                winner_identifiers[index] if index < len(winner_identifiers) else None
            ),
        )
        for index, name in enumerate(winner_names)
    )
    contract_identifier = contract_ids[0] if contract_ids else "default"
    award_at = _aware(notice.award_timestamp()) or published_at
    status = {
        ProcurementPublicationKind.AWARD: ContractStatus.AWARDED,
        ProcurementPublicationKind.AMENDMENT: ContractStatus.ACTIVE,
        ProcurementPublicationKind.CANCELLATION: ContractStatus.CANCELLED,
    }[kind]
    return ProcurementContractProjection(
        contract_key=f"ted:contract:{procedure_key}:{contract_identifier}",
        procedure_key=procedure_key,
        buyer_organization_id=buyer.id,
        title=notice.contract_name() or notice.title(),
        status=status,
        confidence=0.88 if winner_names else 0.8,
        parties=parties,
        service_families=classify_service_families(notice.title()),
        amount=_money_amount(notice),
        award_date=award_at.date() if award_at is not None else None,
        conclusion_date=conclusion_at.date() if conclusion_at is not None else None,
        conclusion_date_basis=(
            DateBasis.PUBLISHED if conclusion_at is not None else DateBasis.UNKNOWN
        ),
    )


def _commercial_projection(
    notice: TedNotice,
    *,
    buyer: Organization,
    matched_terms: tuple[str, ...],
    notice_url: str,
    payload_hash: str,
    published_at: datetime | None,
    deadline: datetime | None,
    collected_at: datetime,
    retention_until: datetime,
) -> CommercialProjection:
    evidence_id = uuid5(NAMESPACE_URL, f"ted:notice:{notice.publication_number}")
    summary = _summary(notice.title(), notice.buyer(), deadline)
    evidence = Evidence(
        id=evidence_id,
        source_id=SOURCE_ID,
        source_record_key=notice.publication_number,
        source_url=notice_url,
        summary=summary,
        confidence=0.9,
        collected_at=collected_at,
        published_at=published_at,
        content_hash_sha256=payload_hash,
        raw_storage_permitted=False,
        retention_until=retention_until,
    )
    signal = CommercialSignal(
        id=uuid5(NAMESPACE_URL, f"ted:signal:{notice.publication_number}"),
        organization_id=buyer.id,
        evidence_id=evidence_id,
        signal_type=SignalType.PUBLIC_TENDER,
        title=notice.title(),
        summary=summary,
        confidence=0.9,
        matched_terms=matched_terms,
        published_at=published_at,
        collected_at=collected_at,
        expires_at=deadline,
        created_at=collected_at,
    )
    return CommercialProjection(buyer, evidence, signal)


def _buyer(notice: TedNotice, *, collected_at: datetime) -> Organization:
    buyer = notice.buyer()
    country = COUNTRY_CODES.get(notice.country() or "")
    return Organization(
        id=uuid5(
            NAMESPACE_URL,
            f"ted:buyer:{country or 'unknown'}:{' '.join(buyer.casefold().split())}",
        ),
        canonical_name=buyer,
        legal_name=buyer,
        country_code=country,
        created_at=collected_at,
        updated_at=collected_at,
    )


def _publication_kind(notice: TedNotice) -> ProcurementPublicationKind:
    notice_types = " ".join(notice.notice_types()).casefold()
    if any(term in notice_types for term in ("cancel", "annul")):
        return ProcurementPublicationKind.CANCELLATION
    if any(term in notice_types for term in ("modif", "change")):
        return ProcurementPublicationKind.AMENDMENT
    if notice.winner_names() or any(
        term in notice_types for term in ("award", "result", "can-")
    ):
        return ProcurementPublicationKind.AWARD
    if any(term in notice_types for term in ("corrig", "rectif")):
        return ProcurementPublicationKind.RECTIFICATION
    return ProcurementPublicationKind.NOTICE


def _procedure_status(kind: ProcurementPublicationKind) -> ProcurementProcedureStatus:
    if kind is ProcurementPublicationKind.CANCELLATION:
        return ProcurementProcedureStatus.CANCELLED
    if kind in {
        ProcurementPublicationKind.AWARD,
        ProcurementPublicationKind.AMENDMENT,
    }:
        return ProcurementProcedureStatus.AWARDED
    return ProcurementProcedureStatus.OPEN


def _record_type(kind: ProcurementPublicationKind) -> str:
    return f"procurement_{kind.value}"


def _is_actionable(
    kind: ProcurementPublicationKind,
    *,
    deadline: datetime | None,
    collected_at: datetime,
) -> bool:
    if kind not in {
        ProcurementPublicationKind.NOTICE,
        ProcurementPublicationKind.RECTIFICATION,
    }:
        return False
    return deadline is None or deadline > collected_at


def _money_amount(notice: TedNotice) -> MoneyAmount | None:
    values = notice.tender_values()
    currencies = notice.tender_currencies()
    if not values or not currencies:
        return None
    normalized = values[0].replace(" ", "").replace(",", ".")
    try:
        return MoneyAmount(value=Decimal(normalized), currency=currencies[0])
    except (InvalidOperation, ValueError):
        return None


def _payload_hash(notice: TedNotice) -> str:
    payload = notice.model_dump(mode="json", by_alias=True)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def _summary(title: str, buyer: str, deadline: datetime | None) -> str:
    result = f"TED public procurement notice from {buyer}: {title}."
    if deadline is not None:
        result += f" Response deadline: {deadline.isoformat()}."
    return result


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

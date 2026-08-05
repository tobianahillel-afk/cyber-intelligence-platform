from __future__ import annotations

import json
from calendar import monthrange
from dataclasses import dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cip.adapters.sources.decp.schemas import DecpContract
from cip.adapters.sources.procurement_signals import matched_procurement_terms
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

SOURCE_ID = "decp"
ADAPTER_ID = "decp-explore-api"
ADAPTER_VERSION = "1.0.0"
DATASET_URL = "https://data.economie.gouv.fr/explore/dataset/decp-2022-marches-valides/"


@dataclass(frozen=True, slots=True)
class DecpMapping:
    observation: RawObservation
    buyer: Organization
    procurement: ProcurementHistoryProjection


def map_decp_contract(
    contract: DecpContract,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> DecpMapping | None:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    matched_terms = matched_procurement_terms(contract.searchable_text())
    if not matched_terms:
        return None
    published_at = _aware(contract.publication_timestamp())
    notification_at = _aware(contract.notification_timestamp())
    duration_months = contract.duration_months()
    end_date = _derived_end_date(notification_at, duration_months)
    payload_hash = _payload_hash(contract)
    buyer = _buyer(contract, collected_at=collected)
    kind = (
        ProcurementPublicationKind.AMENDMENT
        if contract.is_modification()
        else ProcurementPublicationKind.AWARD
    )
    source_record_key = _source_record_key(contract)
    observation = RawObservation(
        source_id=SOURCE_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        collection_job_id=collection_job_id,
        source_record_type=f"procurement_{kind.value}",
        source_record_key=source_record_key,
        source_url=DATASET_URL,
        payload_hash_sha256=payload_hash,
        data_categories=frozenset({DataCategory.PUBLIC_TENDER}),
        collected_at=collected,
        published_at=published_at,
        schema_fingerprint="decp-2022-marches-valides-selected-fields-1",
        content_language="fr",
        classification="internal",
        retention_until=retention_until,
    )
    procedure_key = f"decp:procedure:{contract.id}"
    publication = ProcurementPublication(
        id=uuid5(NAMESPACE_URL, f"decp:publication:{source_record_key}:{payload_hash}"),
        procedure_key=procedure_key,
        source_id=SOURCE_ID,
        source_record_key=source_record_key,
        source_url=DATASET_URL,
        kind=kind,
        procedure_status=ProcurementProcedureStatus.AWARDED,
        buyer_organization_id=buyer.id,
        title=contract.effective_title(),
        content_hash_sha256=payload_hash,
        collected_at=collected,
        published_at=published_at,
        details={
            "contract_id": contract.id,
            "modification_id": contract.idmodification,
            "nature": contract.nature,
            "procedure": contract.procedure,
            "cpv": contract.codecpv,
            "duration_months": duration_months,
            "source": contract.source,
        },
    )
    projection = ProcurementContractProjection(
        contract_key=f"decp:contract:{contract.id}",
        procedure_key=procedure_key,
        buyer_organization_id=buyer.id,
        title=contract.effective_title(),
        status=(
            ContractStatus.ACTIVE if contract.is_modification() else ContractStatus.AWARDED
        ),
        confidence=0.94,
        parties=_parties(contract),
        service_families=classify_service_families(contract.searchable_text()),
        amount=_amount(contract),
        notification_date=(
            notification_at.date() if notification_at is not None else None
        ),
        notification_date_basis=(
            DateBasis.PUBLISHED if notification_at is not None else DateBasis.UNKNOWN
        ),
        end_date=end_date,
        end_date_basis=(DateBasis.DERIVED if end_date is not None else DateBasis.UNKNOWN),
        renewal_date=end_date,
        renewal_date_basis=(
            DateBasis.ESTIMATED if end_date is not None else DateBasis.UNKNOWN
        ),
    )
    return DecpMapping(
        observation=observation,
        buyer=buyer,
        procurement=ProcurementHistoryProjection(
            publication=publication,
            contract=projection,
        ),
    )


def _buyer(contract: DecpContract, *, collected_at: datetime) -> Organization:
    identifier = contract.buyer_identifier()
    registration_ids = _registration_ids(identifier)
    identity_material = registration_ids[0] if registration_ids else contract.acheteur_nom
    return Organization(
        id=uuid5(NAMESPACE_URL, f"decp:buyer:{identity_material.casefold()}"),
        canonical_name=contract.acheteur_nom,
        legal_name=contract.acheteur_nom,
        country_code="FR",
        registration_ids=registration_ids,
        created_at=collected_at,
        updated_at=collected_at,
    )


def _parties(contract: DecpContract) -> tuple[ProcurementParty, ...]:
    return tuple(
        ProcurementParty(
            role=ProcurementPartyRole.AWARDEE,
            published_name=name,
            resolution_status=PartyResolutionStatus.UNRESOLVED,
            confidence=0.82 if identifier else 0.7,
            official_identifier=identifier,
        )
        for name, identifier, _identifier_type in contract.titulars()
    )


def _amount(contract: DecpContract) -> MoneyAmount | None:
    value = contract.amount_value()
    return MoneyAmount(value=value, currency="EUR") if value is not None else None


def _source_record_key(contract: DecpContract) -> str:
    if contract.is_modification():
        modification_id = contract.idmodification or _payload_hash(contract)[:16]
        return f"{contract.id}:modification:{modification_id}"
    return contract.id


def _derived_end_date(
    notification_at: datetime | None,
    duration_months: int | None,
) -> date | None:
    if notification_at is None or duration_months is None:
        return None
    return _add_months(notification_at.date(), duration_months)


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def _registration_ids(identifier: str) -> tuple[str, ...]:
    digits = "".join(character for character in identifier if character.isdigit())
    if len(digits) == 14:
        return (f"SIRET:{digits}",)
    if len(digits) == 9:
        return (f"SIREN:{digits}",)
    return ()


def _payload_hash(contract: DecpContract) -> str:
    payload = contract.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

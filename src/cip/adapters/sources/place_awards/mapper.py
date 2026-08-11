from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cip.adapters.sources.place_awards.schemas import PlaceAward
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

SOURCE_ID = "place-awards"
ADAPTER_ID = "place-open-data-awards-api"
ADAPTER_VERSION = "1.0.0"
DATASET_URL = (
    "https://data.economie.gouv.fr/explore/dataset/"
    "marches-publics-conclus-recenses-sur-la-plateforme-des-achats-de-letat-/"
)


@dataclass(frozen=True, slots=True)
class PlaceAwardMapping:
    observation: RawObservation
    buyer: Organization
    procurement: ProcurementHistoryProjection


def map_place_award(
    award: PlaceAward,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> PlaceAwardMapping:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    payload_hash = _payload_hash(award)
    source_record_key = _source_record_key(award)
    buyer = _buyer(award, collected_at=collected)
    awardee = _awardee(award)
    published_at = datetime.combine(award.date_de_notification, datetime.min.time(), UTC)
    observation = RawObservation(
        source_id=SOURCE_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        collection_job_id=collection_job_id,
        source_record_type="procurement_award",
        source_record_key=source_record_key,
        source_url=DATASET_URL,
        payload_hash_sha256=payload_hash,
        data_categories=frozenset({DataCategory.CONTRACT_AWARD}),
        collected_at=collected,
        published_at=published_at,
        source_updated_at=published_at,
        schema_fingerprint="place-awards-selected-fields-1",
        content_language="fr",
        classification="internal",
        retention_until=retention_until,
    )
    procedure_key = f"place:procedure:{source_record_key}"
    publication = ProcurementPublication(
        id=uuid5(NAMESPACE_URL, f"place:publication:{source_record_key}:{payload_hash}"),
        procedure_key=procedure_key,
        source_id=SOURCE_ID,
        source_record_key=source_record_key,
        source_url=DATASET_URL,
        kind=ProcurementPublicationKind.AWARD,
        procedure_status=ProcurementProcedureStatus.AWARDED,
        buyer_organization_id=buyer.id,
        title=award.objet_du_marche,
        content_hash_sha256=payload_hash,
        collected_at=collected,
        published_at=published_at,
        details={
            "public_entity": award.entite_publique,
            "purchasing_entity": award.entite_d_achat,
            "buyer_postal_code": award.code_postal_entite_d_achat,
            "market_nature": award.nature_du_marche,
            "budget_band": award.tranche_budgetaire,
            "awardee_is_sme": award.attributaire_est_une_pme,
        },
    )
    contract = ProcurementContractProjection(
        contract_key=f"place:contract:{source_record_key}",
        procedure_key=procedure_key,
        buyer_organization_id=buyer.id,
        title=award.objet_du_marche,
        status=ContractStatus.AWARDED,
        confidence=0.9,
        parties=(awardee,) if awardee is not None else (),
        service_families=classify_service_families(award.searchable_text()),
        amount=(
            MoneyAmount(value=award.montant, currency="EUR")
            if award.montant is not None
            else None
        ),
        notification_date=award.date_de_notification,
        notification_date_basis=DateBasis.PUBLISHED,
    )
    return PlaceAwardMapping(
        observation=observation,
        buyer=buyer,
        procurement=ProcurementHistoryProjection(publication=publication, contract=contract),
    )


def _buyer(award: PlaceAward, *, collected_at: datetime) -> Organization:
    name = award.buyer_name()
    normalized = " ".join(name.casefold().split())
    return Organization(
        id=uuid5(NAMESPACE_URL, f"place:buyer-name:{normalized}"),
        canonical_name=name,
        legal_name=name,
        country_code="FR",
        created_at=collected_at,
        updated_at=collected_at,
    )


def _awardee(award: PlaceAward) -> ProcurementParty | None:
    if award.nom_attributaire is None:
        return None
    siret = _normalized_siret(award.siret_attributaire)
    return ProcurementParty(
        role=ProcurementPartyRole.AWARDEE,
        published_name=award.nom_attributaire,
        resolution_status=PartyResolutionStatus.UNRESOLVED,
        confidence=0.84 if siret else 0.7,
        official_identifier=f"SIRET:{siret}" if siret else None,
    )


def _source_record_key(award: PlaceAward) -> str:
    identity = {
        "buyer": award.buyer_name(),
        "awardee": award.nom_attributaire,
        "awardee_siret": _normalized_siret(award.siret_attributaire),
        "date": award.date_de_notification.isoformat(),
        "object": award.objet_du_marche,
        "amount": str(award.montant) if award.montant is not None else None,
        "nature": award.nature_du_marche,
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def _payload_hash(award: PlaceAward) -> str:
    encoded = json.dumps(
        award.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return sha256(encoded).hexdigest()


def _normalized_siret(value: str | None) -> str | None:
    if value is None:
        return None
    digits = "".join(character for character in value if character.isdigit())
    return digits if len(digits) == 14 else None

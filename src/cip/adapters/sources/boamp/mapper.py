from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cip.adapters.sources.boamp.schemas import BoampNotice
from cip.adapters.sources.procurement_signals import matched_procurement_terms
from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.evidence.domain.entities import Evidence
from cip.modules.opportunities.domain.entities import CommercialSignal, SignalType
from cip.modules.organizations.domain.entities import Organization
from cip.modules.procurement_history.domain.models import (
    ContractStatus,
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

SOURCE_ID = "boamp"
ADAPTER_ID = "boamp-explore-api"
ADAPTER_VERSION = "1.1.0"


@dataclass(frozen=True, slots=True)
class BoampMapping:
    observation: RawObservation
    buyer: Organization
    procurement: ProcurementHistoryProjection
    projection: CommercialProjection | None


def map_boamp_notice(
    notice: BoampNotice,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> BoampMapping | None:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    matched_terms = matched_procurement_terms(notice.searchable_text())
    if not matched_terms:
        return None
    published_at = _aware(notice.publication_timestamp())
    deadline = _aware(notice.deadline_timestamp())
    usable_deadline = deadline if deadline is not None and deadline > collected else None
    payload_hash = _payload_hash(notice)
    state = _normalized_state(notice.etat)
    record_type = _record_type(notice, state)
    buyer = _buyer(notice, collected_at=collected)
    observation = _observation(
        notice,
        collection_job_id=collection_job_id,
        collected_at=collected,
        retention_until=retention_until,
        published_at=published_at,
        payload_hash=payload_hash,
        record_type=record_type,
    )
    procurement = _procurement_projection(
        notice,
        buyer=buyer,
        record_type=record_type,
        state=state,
        payload_hash=payload_hash,
        published_at=published_at,
        collected_at=collected,
    )
    commercial = None
    if _is_actionable(record_type, deadline=deadline, collected_at=collected):
        commercial = _commercial_projection(
            notice,
            buyer=buyer,
            matched_terms=matched_terms,
            payload_hash=payload_hash,
            published_at=published_at,
            deadline=usable_deadline,
            collected_at=collected,
            retention_until=retention_until,
        )
    return BoampMapping(
        observation=observation,
        buyer=buyer,
        procurement=procurement,
        projection=commercial,
    )


def _observation(
    notice: BoampNotice,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    published_at: datetime | None,
    payload_hash: str,
    record_type: str,
) -> RawObservation:
    return RawObservation(
        source_id=SOURCE_ID,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        collection_job_id=collection_job_id,
        source_record_type=record_type,
        source_record_key=notice.idweb,
        source_url=notice.notice_url(),
        payload_hash_sha256=payload_hash,
        data_categories=frozenset({DataCategory.PUBLIC_TENDER}),
        collected_at=collected_at,
        published_at=published_at,
        schema_fingerprint="boamp-explore-v2-selected-fields-2",
        content_language="fr",
        classification="internal",
        retention_until=retention_until,
    )


def _procurement_projection(
    notice: BoampNotice,
    *,
    buyer: Organization,
    record_type: str,
    state: str,
    payload_hash: str,
    published_at: datetime | None,
    collected_at: datetime,
) -> ProcurementHistoryProjection:
    awardees = notice.awardee_names()
    kind = _publication_kind(record_type, has_awardees=bool(awardees))
    procedure_status = _procedure_status(record_type)
    procedure_key = f"boamp:procedure:{notice.idweb}"
    publication = ProcurementPublication(
        id=uuid5(NAMESPACE_URL, f"boamp:publication:{notice.idweb}:{payload_hash}"),
        procedure_key=procedure_key,
        source_id=SOURCE_ID,
        source_record_key=notice.idweb,
        source_url=notice.notice_url(),
        kind=kind,
        procedure_status=procedure_status,
        buyer_organization_id=buyer.id,
        title=notice.objet,
        content_hash_sha256=payload_hash,
        collected_at=collected_at,
        published_at=published_at,
        details={
            "record_type": record_type,
            "state": state or "initial",
            "awardees": list(awardees),
        },
    )
    contract = _contract_projection(
        notice,
        buyer=buyer,
        publication_kind=kind,
        procedure_key=procedure_key,
        awardees=awardees,
        published_at=published_at,
    )
    return ProcurementHistoryProjection(publication=publication, contract=contract)


def _contract_projection(
    notice: BoampNotice,
    *,
    buyer: Organization,
    publication_kind: ProcurementPublicationKind,
    procedure_key: str,
    awardees: tuple[str, ...],
    published_at: datetime | None,
) -> ProcurementContractProjection | None:
    if not awardees or publication_kind not in {
        ProcurementPublicationKind.AWARD,
        ProcurementPublicationKind.CANCELLATION,
    }:
        return None
    status = (
        ContractStatus.CANCELLED
        if publication_kind is ProcurementPublicationKind.CANCELLATION
        else ContractStatus.AWARDED
    )
    parties = tuple(
        ProcurementParty(
            role=ProcurementPartyRole.AWARDEE,
            published_name=name,
            resolution_status=PartyResolutionStatus.UNRESOLVED,
            confidence=0.7,
        )
        for name in awardees
    )
    return ProcurementContractProjection(
        contract_key=f"boamp:contract:{notice.idweb}:default",
        procedure_key=procedure_key,
        buyer_organization_id=buyer.id,
        title=notice.objet,
        status=status,
        confidence=0.82,
        parties=parties,
        service_families=classify_service_families(notice.searchable_text()),
        award_date=published_at.date() if published_at is not None else None,
    )


def _commercial_projection(
    notice: BoampNotice,
    *,
    buyer: Organization,
    matched_terms: tuple[str, ...],
    payload_hash: str,
    published_at: datetime | None,
    deadline: datetime | None,
    collected_at: datetime,
    retention_until: datetime,
) -> CommercialProjection:
    evidence_id = uuid5(NAMESPACE_URL, f"boamp:notice:{notice.idweb}")
    summary = _summary(notice, deadline=deadline)
    evidence = Evidence(
        id=evidence_id,
        source_id=SOURCE_ID,
        source_record_key=notice.idweb,
        source_url=notice.notice_url(),
        summary=summary,
        confidence=0.92,
        collected_at=collected_at,
        published_at=published_at,
        content_hash_sha256=payload_hash,
        raw_storage_permitted=False,
        retention_until=retention_until,
    )
    signal = CommercialSignal(
        id=uuid5(NAMESPACE_URL, f"boamp:signal:{notice.idweb}"),
        organization_id=buyer.id,
        evidence_id=evidence_id,
        signal_type=SignalType.PUBLIC_TENDER,
        title=notice.objet,
        summary=summary,
        confidence=0.92,
        matched_terms=matched_terms,
        published_at=published_at,
        collected_at=collected_at,
        expires_at=deadline,
        created_at=collected_at,
    )
    return CommercialProjection(buyer, evidence, signal)


def _buyer(notice: BoampNotice, *, collected_at: datetime) -> Organization:
    buyer = notice.nomacheteur
    return Organization(
        id=uuid5(
            NAMESPACE_URL,
            f"boamp:buyer:fr:{' '.join(buyer.casefold().split())}",
        ),
        canonical_name=buyer,
        legal_name=buyer,
        country_code="FR",
        created_at=collected_at,
        updated_at=collected_at,
    )


def _record_type(notice: BoampNotice, state: str) -> str:
    searchable = notice.searchable_text().casefold()
    if state == "annulation":
        return "procurement_cancellation"
    if any(term in searchable for term in ("résultat", "resultat", "attribution")):
        return "procurement_result"
    if state == "rectificatif":
        return "procurement_rectification"
    return "procurement_notice"


def _publication_kind(
    record_type: str,
    *,
    has_awardees: bool,
) -> ProcurementPublicationKind:
    if record_type == "procurement_cancellation":
        return ProcurementPublicationKind.CANCELLATION
    if record_type == "procurement_result":
        if has_awardees:
            return ProcurementPublicationKind.AWARD
        return ProcurementPublicationKind.RESULT
    if record_type == "procurement_rectification":
        return ProcurementPublicationKind.RECTIFICATION
    return ProcurementPublicationKind.NOTICE


def _procedure_status(record_type: str) -> ProcurementProcedureStatus:
    if record_type == "procurement_cancellation":
        return ProcurementProcedureStatus.CANCELLED
    if record_type == "procurement_result":
        return ProcurementProcedureStatus.AWARDED
    return ProcurementProcedureStatus.OPEN


def _is_actionable(
    record_type: str,
    *,
    deadline: datetime | None,
    collected_at: datetime,
) -> bool:
    if record_type in {"procurement_cancellation", "procurement_result"}:
        return False
    return deadline is None or deadline > collected_at


def _summary(notice: BoampNotice, *, deadline: datetime | None) -> str:
    state = _normalized_state(notice.etat) or "initial"
    summary = f"BOAMP {state} notice from {notice.nomacheteur}: {notice.objet}."
    if deadline is not None:
        summary += f" Response deadline: {deadline.isoformat()}."
    return summary


def _payload_hash(notice: BoampNotice) -> str:
    payload = notice.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def _normalized_state(value: str | None) -> str:
    return value.strip().casefold() if value else ""


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

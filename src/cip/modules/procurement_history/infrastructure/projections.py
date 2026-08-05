from __future__ import annotations

from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from cip.modules.procurement_history.domain.models import (
    ProcurementContractProjection,
    ProcurementHistoryProjection,
    ProcurementPublication,
)
from cip.modules.procurement_history.infrastructure.models import (
    ProcurementContractPartyRecord,
    ProcurementContractRecord,
    ProcurementProcedureRecord,
    ProcurementPublicationRecord,
    ProcurementServiceClassificationRecord,
)
from cip.shared.kernel.time import require_aware_utc


def persist_procurement_projections(
    session: Session,
    projections: tuple[ProcurementHistoryProjection, ...],
    *,
    now: datetime,
) -> None:
    updated_at = require_aware_utc(now, field_name="now")
    for projection in projections:
        publication = projection.publication
        procedure = _upsert_procedure(session, publication, now=updated_at)
        publication_record = _insert_publication(session, procedure.id, publication)
        if projection.contract is None:
            continue
        contract, changed = _upsert_contract(
            session,
            procedure.id,
            publication_record,
            projection.contract,
            now=updated_at,
        )
        if changed:
            _replace_parties(session, contract.id, projection.contract)
            _replace_service_families(session, contract.id, projection.contract)


def _upsert_procedure(
    session: Session,
    publication: ProcurementPublication,
    *,
    now: datetime,
) -> ProcurementProcedureRecord:
    record = session.scalar(
        select(ProcurementProcedureRecord).where(
            ProcurementProcedureRecord.canonical_key == publication.procedure_key
        )
    )
    effective_at = publication.published_at or publication.collected_at
    if record is None:
        record = ProcurementProcedureRecord(
            id=uuid5(NAMESPACE_URL, f"procurement:procedure:{publication.procedure_key}"),
            canonical_key=publication.procedure_key,
            buyer_organization_id=publication.buyer_organization_id,
            title=publication.title,
            status=publication.procedure_status.value,
            first_published_at=publication.published_at,
            latest_published_at=publication.published_at,
            source_ids=[publication.source_id],
            created_at=now,
            updated_at=now,
        )
        session.add(record)
        session.flush()
        return record
    if record.buyer_organization_id != publication.buyer_organization_id:
        raise ValueError("procedure buyer identity cannot change")
    record.source_ids = sorted(set(record.source_ids) | {publication.source_id})
    if record.first_published_at is None or (
        publication.published_at is not None
        and publication.published_at < record.first_published_at
    ):
        record.first_published_at = publication.published_at
    latest = record.latest_published_at
    if latest is None or effective_at >= latest:
        record.title = publication.title
        record.status = publication.procedure_status.value
        record.latest_published_at = publication.published_at or effective_at
    record.updated_at = now
    session.flush()
    return record


def _insert_publication(
    session: Session,
    procedure_id: UUID,
    publication: ProcurementPublication,
) -> ProcurementPublicationRecord:
    existing = session.scalar(
        select(ProcurementPublicationRecord).where(
            ProcurementPublicationRecord.revision_key == publication.revision_key
        )
    )
    if existing is not None:
        if existing.procedure_id != procedure_id:
            raise ValueError("publication revision cannot move to another procedure")
        return existing
    record = ProcurementPublicationRecord(
        id=publication.id,
        procedure_id=procedure_id,
        evidence_id=publication.evidence_id,
        source_id=publication.source_id,
        source_record_key=publication.source_record_key,
        revision_key=publication.revision_key,
        kind=publication.kind.value,
        procedure_status=publication.procedure_status.value,
        source_url=publication.source_url,
        content_hash_sha256=publication.content_hash_sha256,
        title=publication.title,
        published_at=publication.published_at,
        collected_at=publication.collected_at,
        details=dict(publication.details),
    )
    session.add(record)
    session.flush()
    return record


def _upsert_contract(
    session: Session,
    procedure_id: UUID,
    publication: ProcurementPublicationRecord,
    projection: ProcurementContractProjection,
    *,
    now: datetime,
) -> tuple[ProcurementContractRecord, bool]:
    record = session.scalar(
        select(ProcurementContractRecord).where(
            ProcurementContractRecord.contract_key == projection.contract_key
        )
    )
    if record is None:
        record = ProcurementContractRecord(
            id=uuid5(NAMESPACE_URL, f"procurement:contract:{projection.contract_key}"),
            contract_key=projection.contract_key,
            procedure_id=procedure_id,
            buyer_organization_id=projection.buyer_organization_id,
            latest_publication_id=publication.id,
            title=projection.title,
            status=projection.status.value,
            created_at=now,
            updated_at=now,
            **_contract_values(projection),
        )
        session.add(record)
        session.flush()
        return record, True
    if record.procedure_id != procedure_id:
        raise ValueError("contract cannot move to another procedure")
    if record.buyer_organization_id != projection.buyer_organization_id:
        raise ValueError("contract buyer identity cannot change")
    if not _publication_is_newer(session, record.latest_publication_id, publication):
        return record, False
    record.latest_publication_id = publication.id
    record.title = projection.title
    record.status = projection.status.value
    for field_name, value in _contract_values(projection).items():
        setattr(record, field_name, value)
    record.updated_at = now
    session.flush()
    return record, True


def _publication_is_newer(
    session: Session,
    current_publication_id: UUID,
    candidate: ProcurementPublicationRecord,
) -> bool:
    current = session.get(ProcurementPublicationRecord, current_publication_id)
    if current is None:
        return True
    current_time = current.published_at or current.collected_at
    candidate_time = candidate.published_at or candidate.collected_at
    if candidate_time != current_time:
        return candidate_time > current_time
    return candidate.revision_key >= current.revision_key


def _contract_values(projection: ProcurementContractProjection) -> dict[str, object]:
    amount = projection.amount
    return {
        "amount_value": amount.value if amount else None,
        "amount_upper_value": amount.upper_value if amount else None,
        "currency": amount.currency if amount else None,
        "amount_type": amount.amount_type.value if amount else None,
        "award_date": projection.award_date,
        "start_date": projection.start_date,
        "start_date_basis": projection.start_date_basis.value,
        "end_date": projection.end_date,
        "end_date_basis": projection.end_date_basis.value,
        "renewal_date": projection.renewal_date,
        "renewal_date_basis": projection.renewal_date_basis.value,
        "confidence": projection.confidence,
    }


def _replace_parties(
    session: Session,
    contract_id: UUID,
    projection: ProcurementContractProjection,
) -> None:
    session.execute(
        delete(ProcurementContractPartyRecord).where(
            ProcurementContractPartyRecord.contract_id == contract_id
        )
    )
    session.add_all(
        ProcurementContractPartyRecord(
            contract_id=contract_id,
            party_key=party.identity_key,
            role=party.role.value,
            organization_id=party.organization_id,
            published_name=party.published_name,
            resolution_status=party.resolution_status.value,
            confidence=party.confidence,
            official_identifier=party.official_identifier,
        )
        for party in projection.parties
    )


def _replace_service_families(
    session: Session,
    contract_id: UUID,
    projection: ProcurementContractProjection,
) -> None:
    session.execute(
        delete(ProcurementServiceClassificationRecord).where(
            ProcurementServiceClassificationRecord.contract_id == contract_id
        )
    )
    session.add_all(
        ProcurementServiceClassificationRecord(
            contract_id=contract_id,
            family=match.family.value,
            matched_terms=list(match.matched_terms),
            confidence=match.confidence,
        )
        for match in projection.service_families
    )

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.procurement_history.application.view_models import (
    ProcurementContractDetail,
    ProcurementContractListItem,
    ProcurementContractPage,
    ProcurementPartyItem,
    ProcurementPublicationItem,
    ProcurementServiceFamilyItem,
)
from cip.modules.procurement_history.domain.models import ContractStatus
from cip.modules.procurement_history.infrastructure.errors import (
    ProcurementContractNotFoundError,
)
from cip.modules.procurement_history.infrastructure.models import (
    ProcurementContractPartyRecord,
    ProcurementContractRecord,
    ProcurementProcedureRecord,
    ProcurementPublicationRecord,
    ProcurementServiceClassificationRecord,
)
from cip.modules.service_taxonomy.domain.models import (
    CyberServiceFamily,
    service_family_identifiers,
)
from cip.shared.kernel.time import require_aware_utc


def list_procurement_contracts(
    session: Session,
    *,
    now: datetime,
    statuses: tuple[ContractStatus, ...] = (),
    family: CyberServiceFamily | None = None,
    buyer_organization_id: UUID | None = None,
    renewal_from: date | None = None,
    renewal_to: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ProcurementContractPage:
    generated_at = require_aware_utc(now, field_name="now")
    _validate_list_options(
        renewal_from=renewal_from,
        renewal_to=renewal_to,
        limit=limit,
        offset=offset,
    )
    filters: list[ColumnElement[bool]] = []
    if statuses:
        filters.append(ProcurementContractRecord.status.in_(status.value for status in statuses))
    if buyer_organization_id is not None:
        filters.append(
            ProcurementContractRecord.buyer_organization_id == buyer_organization_id
        )
    if renewal_from is not None:
        filters.append(ProcurementContractRecord.renewal_date >= renewal_from)
    if renewal_to is not None:
        filters.append(ProcurementContractRecord.renewal_date <= renewal_to)

    count_query = select(func.count(func.distinct(ProcurementContractRecord.id)))
    record_query = select(ProcurementContractRecord)
    if family is not None:
        count_query = count_query.join(
            ProcurementServiceClassificationRecord,
            ProcurementServiceClassificationRecord.contract_id
            == ProcurementContractRecord.id,
        )
        record_query = record_query.join(
            ProcurementServiceClassificationRecord,
            ProcurementServiceClassificationRecord.contract_id
            == ProcurementContractRecord.id,
        )
        filters.append(
            ProcurementServiceClassificationRecord.family.in_(
                service_family_identifiers(family)
            )
        )

    total = int(session.scalar(count_query.where(*filters)) or 0)
    records = tuple(
        session.scalars(
            record_query.where(*filters)
            .distinct()
            .order_by(
                ProcurementContractRecord.renewal_date.is_(None),
                ProcurementContractRecord.renewal_date.asc(),
                ProcurementContractRecord.updated_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
    )
    return ProcurementContractPage(
        items=tuple(_list_item(session, record) for record in records),
        total=total,
        limit=limit,
        offset=offset,
        generated_at=generated_at,
    )


def get_procurement_contract_detail(
    session: Session,
    contract_id: UUID,
) -> ProcurementContractDetail:
    record = session.get(ProcurementContractRecord, contract_id)
    if record is None:
        raise ProcurementContractNotFoundError(str(contract_id))
    procedure = session.get(ProcurementProcedureRecord, record.procedure_id)
    if procedure is None:
        raise RuntimeError("procurement contract procedure is missing")
    parties = tuple(
        session.scalars(
            select(ProcurementContractPartyRecord)
            .where(ProcurementContractPartyRecord.contract_id == contract_id)
            .order_by(
                ProcurementContractPartyRecord.role,
                ProcurementContractPartyRecord.published_name,
            )
        )
    )
    classifications = tuple(
        session.scalars(
            select(ProcurementServiceClassificationRecord)
            .where(ProcurementServiceClassificationRecord.contract_id == contract_id)
            .order_by(ProcurementServiceClassificationRecord.family)
        )
    )
    publications = tuple(
        session.scalars(
            select(ProcurementPublicationRecord)
            .where(ProcurementPublicationRecord.procedure_id == procedure.id)
            .order_by(
                ProcurementPublicationRecord.published_at.asc(),
                ProcurementPublicationRecord.collected_at.asc(),
                ProcurementPublicationRecord.revision_key.asc(),
            )
        )
    )
    buyer = session.get(OrganizationRecord, record.buyer_organization_id)
    if buyer is None:
        raise RuntimeError("procurement contract buyer organization is missing")
    return ProcurementContractDetail(
        id=record.id,
        procedure_id=record.procedure_id,
        procedure_key=procedure.procedure_key,
        buyer_organization_id=record.buyer_organization_id,
        buyer_name=buyer.canonical_name,
        title=record.title,
        status=ContractStatus(record.status),
        confidence=record.confidence,
        amount_value=record.amount_value,
        amount_currency=record.amount_currency,
        amount_type=record.amount_type,
        amount_upper_value=record.amount_upper_value,
        award_date=record.award_date,
        conclusion_date=record.conclusion_date,
        conclusion_date_basis=record.conclusion_date_basis,
        notification_date=record.notification_date,
        notification_date_basis=record.notification_date_basis,
        start_date=record.start_date,
        start_date_basis=record.start_date_basis,
        end_date=record.end_date,
        end_date_basis=record.end_date_basis,
        renewal_date=record.renewal_date,
        renewal_date_basis=record.renewal_date_basis,
        created_at=database_utc(record.created_at),
        updated_at=database_utc(record.updated_at),
        parties=tuple(_party_item(party) for party in parties),
        service_families=tuple(
            ProcurementServiceFamilyItem(
                family=classification.family,
                confidence=classification.confidence,
                matched_terms=tuple(classification.matched_terms),
            )
            for classification in classifications
        ),
        publications=tuple(_publication_item(publication) for publication in publications),
    )


def _list_item(
    session: Session,
    record: ProcurementContractRecord,
) -> ProcurementContractListItem:
    buyer_name = session.scalar(
        select(OrganizationRecord.canonical_name).where(
            OrganizationRecord.id == record.buyer_organization_id
        )
    )
    if buyer_name is None:
        raise RuntimeError("procurement contract buyer organization is missing")
    classifications = tuple(
        session.scalars(
            select(ProcurementServiceClassificationRecord)
            .where(ProcurementServiceClassificationRecord.contract_id == record.id)
            .order_by(ProcurementServiceClassificationRecord.family)
        )
    )
    return ProcurementContractListItem(
        id=record.id,
        procedure_id=record.procedure_id,
        procedure_key=record.procedure_key,
        buyer_organization_id=record.buyer_organization_id,
        buyer_name=buyer_name,
        title=record.title,
        status=ContractStatus(record.status),
        confidence=record.confidence,
        amount_value=record.amount_value,
        amount_currency=record.amount_currency,
        amount_type=record.amount_type,
        renewal_date=record.renewal_date,
        renewal_date_basis=record.renewal_date_basis,
        updated_at=database_utc(record.updated_at),
        service_families=tuple(
            ProcurementServiceFamilyItem(
                family=classification.family,
                confidence=classification.confidence,
                matched_terms=tuple(classification.matched_terms),
            )
            for classification in classifications
        ),
    )


def _party_item(record: ProcurementContractPartyRecord) -> ProcurementPartyItem:
    return ProcurementPartyItem(
        role=record.role,
        published_name=record.published_name,
        resolution_status=record.resolution_status,
        confidence=record.confidence,
        organization_id=record.organization_id,
        official_identifier=record.official_identifier,
    )


def _publication_item(
    record: ProcurementPublicationRecord,
) -> ProcurementPublicationItem:
    return ProcurementPublicationItem(
        id=record.id,
        source_id=record.source_id,
        source_record_key=record.source_record_key,
        source_url=record.source_url,
        kind=record.kind,
        procedure_status=record.procedure_status,
        title=record.title,
        published_at=(database_utc(record.published_at) if record.published_at else None),
        collected_at=database_utc(record.collected_at),
        details=record.details,
    )


def _validate_list_options(
    *,
    renewal_from: date | None,
    renewal_to: date | None,
    limit: int,
    offset: int,
) -> None:
    if renewal_from is not None and renewal_to is not None and renewal_from > renewal_to:
        raise ValueError("renewal_from cannot be later than renewal_to")
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    if offset < 0:
        raise ValueError("offset cannot be negative")


def database_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

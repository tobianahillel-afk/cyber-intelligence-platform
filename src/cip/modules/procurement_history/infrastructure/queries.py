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
from cip.modules.service_taxonomy.domain.models import CyberServiceFamily
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
        filters.append(ProcurementServiceClassificationRecord.family == family.value)

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
    return ProcurementContractDetail(
        contract=_list_item(session, record),
        contract_key=record.contract_key,
        procedure_key=procedure.canonical_key,
        procedure_title=procedure.title,
        procedure_status=procedure.status,
        first_published_at=_optional_database_utc(procedure.first_published_at),
        latest_published_at=_optional_database_utc(procedure.latest_published_at),
        parties=tuple(_party_item(item) for item in parties),
        service_classifications=tuple(
            _classification_item(item) for item in classifications
        ),
        publications=tuple(_publication_item(item) for item in publications),
    )


def _list_item(
    session: Session,
    record: ProcurementContractRecord,
) -> ProcurementContractListItem:
    buyer = session.get(OrganizationRecord, record.buyer_organization_id)
    procedure = session.get(ProcurementProcedureRecord, record.procedure_id)
    if buyer is None or procedure is None:
        raise RuntimeError("procurement contract references missing records")
    provider_names = tuple(
        session.scalars(
            select(ProcurementContractPartyRecord.published_name)
            .where(
                ProcurementContractPartyRecord.contract_id == record.id,
                ProcurementContractPartyRecord.role.in_(("awardee", "consortium_member")),
            )
            .order_by(ProcurementContractPartyRecord.published_name)
        )
    )
    families = tuple(
        session.scalars(
            select(ProcurementServiceClassificationRecord.family)
            .where(ProcurementServiceClassificationRecord.contract_id == record.id)
            .order_by(ProcurementServiceClassificationRecord.family)
        )
    )
    return ProcurementContractListItem(
        id=record.id,
        procedure_id=record.procedure_id,
        buyer_organization_id=record.buyer_organization_id,
        buyer_name=buyer.canonical_name,
        title=record.title,
        status=record.status,
        amount_value=record.amount_value,
        amount_upper_value=record.amount_upper_value,
        currency=record.currency,
        amount_type=record.amount_type,
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
        confidence=record.confidence,
        provider_names=provider_names,
        service_families=families,
        source_ids=tuple(str(value) for value in procedure.source_ids),
        updated_at=_database_utc(record.updated_at),
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


def _classification_item(
    record: ProcurementServiceClassificationRecord,
) -> ProcurementServiceFamilyItem:
    return ProcurementServiceFamilyItem(
        family=record.family,
        matched_terms=tuple(str(value) for value in record.matched_terms),
        confidence=record.confidence,
    )


def _publication_item(record: ProcurementPublicationRecord) -> ProcurementPublicationItem:
    return ProcurementPublicationItem(
        id=record.id,
        source_id=record.source_id,
        source_record_key=record.source_record_key,
        kind=record.kind,
        procedure_status=record.procedure_status,
        title=record.title,
        source_url=record.source_url,
        published_at=_optional_database_utc(record.published_at),
        collected_at=_database_utc(record.collected_at),
        details=dict(record.details),
    )


def _validate_list_options(
    *,
    renewal_from: date | None,
    renewal_to: date | None,
    limit: int,
    offset: int,
) -> None:
    if renewal_from is not None and renewal_to is not None and renewal_to < renewal_from:
        raise ValueError("renewal_to cannot precede renewal_from")
    if not 1 <= limit <= 200 or offset < 0:
        raise ValueError("invalid pagination")


def _database_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _optional_database_utc(value: datetime | None) -> datetime | None:
    return None if value is None else _database_utc(value)

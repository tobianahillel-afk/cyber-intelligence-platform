from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.professional_context.domain import (
    ProfessionalPersonProjection,
    ProfessionalPersonReference,
    reconcile_person_references,
)
from cip.modules.professional_context.infrastructure.person_models import (
    ProfessionalPersonRecord,
    ProfessionalPersonSnapshotRecord,
)
from cip.modules.professional_context.infrastructure.projection_hydration import person_snapshot
from cip.modules.professional_context.infrastructure.projection_payloads import (
    person_snapshot_digest,
)
from cip.shared.kernel.time import require_aware_utc


def persist_professional_people(
    session: Session,
    references: Iterable[ProfessionalPersonReference],
    *,
    now: datetime,
) -> tuple[ProfessionalPersonRecord, ...]:
    current = require_aware_utc(now, field_name="now")
    grouped: dict[str, list[ProfessionalPersonReference]] = defaultdict(list)
    for reference in references:
        grouped[reference.person_key].append(reference)
    records: list[ProfessionalPersonRecord] = []
    for person_key, incoming in grouped.items():
        record = session.scalar(
            select(ProfessionalPersonRecord).where(
                ProfessionalPersonRecord.person_key == person_key
            )
        )
        if record is None:
            projection = reconcile_person_references(incoming, now=current)
            record = _new_record(projection, current)
            session.add(record)
            session.flush()
        _insert_snapshots(session, record, incoming, current)
        session.flush()
        history = tuple(
            person_snapshot(item)
            for item in session.scalars(
                select(ProfessionalPersonSnapshotRecord)
                .where(ProfessionalPersonSnapshotRecord.person_id == record.id)
                .order_by(ProfessionalPersonSnapshotRecord.observed_at)
            )
        )
        _apply_projection(record, reconcile_person_references(history, now=current), current)
        records.append(record)
    session.flush()
    return tuple(records)


def _insert_snapshots(
    session: Session,
    record: ProfessionalPersonRecord,
    incoming: list[ProfessionalPersonReference],
    now: datetime,
) -> None:
    for item in incoming:
        digest = person_snapshot_digest(item)
        if session.scalar(
            select(ProfessionalPersonSnapshotRecord.id).where(
                ProfessionalPersonSnapshotRecord.snapshot_key == digest
            )
        ):
            continue
        session.add(
            ProfessionalPersonSnapshotRecord(
                id=uuid4(),
                person_id=record.id,
                snapshot_key=digest,
                person_key=item.person_key,
                display_name=item.display_name,
                source_id=item.source_id,
                source_kind=item.source_kind,
                source_record_key=item.source_record_key,
                source_url=item.source_url,
                observed_at=item.observed_at,
                confidence=item.confidence,
                review_state=item.review_state.value,
                lawful_basis=item.processing.lawful_basis.value,
                lawful_basis_reference=item.processing.lawful_basis_reference,
                processing_purpose=item.processing.purpose,
                processing_reviewed_at=item.processing.reviewed_at,
                retention_until=item.processing.retention_until,
                active=item.active,
                suppressed=item.suppressed,
                deleted=item.deleted,
                created_at=now,
            )
        )


def _new_record(
    projection: ProfessionalPersonProjection,
    now: datetime,
) -> ProfessionalPersonRecord:
    record = ProfessionalPersonRecord(
        id=uuid4(),
        person_key=projection.person_key,
        display_name=projection.display_name,
        source_id=projection.source_id,
        confidence=projection.confidence,
        review_state=projection.review_state.value,
        lawful_basis=projection.lawful_basis.value,
        lawful_basis_reference=projection.lawful_basis_reference,
        processing_purpose=projection.purpose,
        current=projection.current,
        suppressed=projection.suppressed,
        deleted=projection.deleted,
        last_observed_at=projection.last_observed_at,
        retention_until=projection.retention_until,
        created_at=now,
        updated_at=now,
    )
    return record


def _apply_projection(
    record: ProfessionalPersonRecord,
    projection: ProfessionalPersonProjection,
    now: datetime,
) -> None:
    record.display_name = projection.display_name
    record.source_id = projection.source_id
    record.confidence = projection.confidence
    record.review_state = projection.review_state.value
    record.lawful_basis = projection.lawful_basis.value
    record.lawful_basis_reference = projection.lawful_basis_reference
    record.processing_purpose = projection.purpose
    record.current = projection.current
    record.suppressed = projection.suppressed
    record.deleted = projection.deleted
    record.last_observed_at = projection.last_observed_at
    record.retention_until = projection.retention_until
    record.updated_at = now

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.professional_context.domain import (
    ProfessionalContactEvidence,
    ProfessionalContactProjection,
    reconcile_contact_evidence,
)
from cip.modules.professional_context.infrastructure.contact_models import (
    ProfessionalContactRecord,
    ProfessionalContactSnapshotRecord,
)
from cip.modules.professional_context.infrastructure.projection_hydration import contact_snapshot
from cip.modules.professional_context.infrastructure.projection_payloads import (
    contact_snapshot_digest,
)
from cip.shared.kernel.time import require_aware_utc


def persist_professional_contacts(
    session: Session,
    evidence: Iterable[ProfessionalContactEvidence],
    *,
    now: datetime,
) -> tuple[ProfessionalContactRecord, ...]:
    current = require_aware_utc(now, field_name="now")
    grouped: dict[str, list[ProfessionalContactEvidence]] = defaultdict(list)
    for item in evidence:
        grouped[item.contact_key].append(item)
    records: list[ProfessionalContactRecord] = []
    for contact_key, incoming in grouped.items():
        record = session.scalar(
            select(ProfessionalContactRecord).where(
                ProfessionalContactRecord.contact_key == contact_key
            )
        )
        if record is None:
            record = _new_record(reconcile_contact_evidence(incoming, now=current), current)
            session.add(record)
            session.flush()
        _insert_snapshots(session, record, incoming, current)
        session.flush()
        history = tuple(
            contact_snapshot(item)
            for item in session.scalars(
                select(ProfessionalContactSnapshotRecord)
                .where(ProfessionalContactSnapshotRecord.contact_id == record.id)
                .order_by(ProfessionalContactSnapshotRecord.observed_at)
            )
        )
        _apply_projection(record, reconcile_contact_evidence(history, now=current), current)
        records.append(record)
    session.flush()
    return tuple(records)


def _insert_snapshots(
    session: Session,
    record: ProfessionalContactRecord,
    incoming: list[ProfessionalContactEvidence],
    now: datetime,
) -> None:
    for item in incoming:
        digest = contact_snapshot_digest(item)
        if session.scalar(
            select(ProfessionalContactSnapshotRecord.id).where(
                ProfessionalContactSnapshotRecord.snapshot_key == digest
            )
        ):
            continue
        session.add(
            ProfessionalContactSnapshotRecord(
                id=uuid4(),
                contact_id=record.id,
                snapshot_key=digest,
                contact_key=item.contact_key,
                channel_type=item.channel_type.value,
                evidence_scope=item.evidence_scope.value,
                value=item.value,
                organization_id=item.organization_id,
                person_key=item.person_key,
                source_id=item.source_id,
                source_record_key=item.source_record_key,
                source_url=item.source_url,
                claim_type=item.claim_type.value,
                review_state=item.review_state.value,
                observed_at=item.observed_at,
                confidence=item.confidence,
                active=item.active,
                suppressed=item.suppressed,
                deleted=item.deleted,
                supersedes_record_key=item.supersedes_record_key,
                lawful_basis=item.processing.lawful_basis.value,
                lawful_basis_reference=item.processing.lawful_basis_reference,
                processing_purpose=item.processing.purpose,
                processing_reviewed_at=item.processing.reviewed_at,
                retention_until=item.processing.retention_until,
                created_at=now,
            )
        )


def _new_record(
    projection: ProfessionalContactProjection,
    now: datetime,
) -> ProfessionalContactRecord:
    return ProfessionalContactRecord(
        id=uuid4(),
        contact_key=projection.contact_key,
        channel_type=projection.channel_type.value,
        value=projection.value,
        organization_id=projection.organization_id,
        person_key=projection.person_key,
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


def _apply_projection(
    record: ProfessionalContactRecord,
    projection: ProfessionalContactProjection,
    now: datetime,
) -> None:
    record.channel_type = projection.channel_type.value
    record.value = projection.value
    record.organization_id = projection.organization_id
    record.person_key = projection.person_key
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

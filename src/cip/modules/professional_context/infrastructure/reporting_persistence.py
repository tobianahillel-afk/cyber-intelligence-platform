from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.professional_context.domain import (
    ReportingLineClaim,
    ReportingLineProjection,
    reconcile_reporting_claims,
)
from cip.modules.professional_context.infrastructure.projection_hydration import reporting_snapshot
from cip.modules.professional_context.infrastructure.projection_payloads import (
    reporting_snapshot_digest,
)
from cip.modules.professional_context.infrastructure.role_models import (
    ProfessionalReportingLineRecord,
    ProfessionalReportingSnapshotRecord,
)
from cip.shared.kernel.time import require_aware_utc


def persist_reporting_lines(
    session: Session,
    claims: Iterable[ReportingLineClaim],
    *,
    now: datetime,
) -> tuple[ProfessionalReportingLineRecord, ...]:
    current = require_aware_utc(now, field_name="now")
    grouped: dict[str, list[ReportingLineClaim]] = defaultdict(list)
    for claim in claims:
        grouped[claim.claim_key].append(claim)
    records: list[ProfessionalReportingLineRecord] = []
    for claim_key, incoming in grouped.items():
        record = session.scalar(
            select(ProfessionalReportingLineRecord).where(
                ProfessionalReportingLineRecord.claim_key == claim_key
            )
        )
        if record is None:
            record = _new_record(reconcile_reporting_claims(incoming, now=current), current)
            session.add(record)
            session.flush()
        _insert_snapshots(session, record, incoming, current)
        session.flush()
        history = tuple(
            reporting_snapshot(item)
            for item in session.scalars(
                select(ProfessionalReportingSnapshotRecord)
                .where(ProfessionalReportingSnapshotRecord.reporting_line_id == record.id)
                .order_by(ProfessionalReportingSnapshotRecord.observed_at)
            )
        )
        _apply_projection(record, reconcile_reporting_claims(history, now=current), current)
        records.append(record)
    session.flush()
    return tuple(records)


def _insert_snapshots(
    session: Session,
    record: ProfessionalReportingLineRecord,
    incoming: list[ReportingLineClaim],
    now: datetime,
) -> None:
    for item in incoming:
        digest = reporting_snapshot_digest(item)
        if session.scalar(
            select(ProfessionalReportingSnapshotRecord.id).where(
                ProfessionalReportingSnapshotRecord.snapshot_key == digest
            )
        ):
            continue
        session.add(
            ProfessionalReportingSnapshotRecord(
                id=uuid4(),
                reporting_line_id=record.id,
                snapshot_key=digest,
                claim_key=item.claim_key,
                subject_person_key=item.subject_person_key,
                manager_person_key=item.manager_person_key,
                organization_id=item.organization_id,
                source_id=item.source_id,
                source_record_key=item.source_record_key,
                source_url=item.source_url,
                claim_type=item.claim_type.value,
                review_state=item.review_state.value,
                observed_at=item.observed_at,
                valid_from=item.valid_from,
                valid_until=item.valid_until,
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
    projection: ReportingLineProjection,
    now: datetime,
) -> ProfessionalReportingLineRecord:
    return ProfessionalReportingLineRecord(
        id=uuid4(),
        claim_key=projection.claim_key,
        subject_person_key=projection.subject_person_key,
        manager_person_key=projection.manager_person_key,
        organization_id=projection.organization_id,
        confidence=projection.confidence,
        review_state=projection.review_state.value,
        lawful_basis=projection.lawful_basis.value,
        lawful_basis_reference=projection.lawful_basis_reference,
        processing_purpose=projection.purpose,
        current=projection.current,
        suppressed=projection.suppressed,
        deleted=projection.deleted,
        first_observed_at=projection.first_observed_at,
        last_observed_at=projection.last_observed_at,
        retention_until=projection.retention_until,
        created_at=now,
        updated_at=now,
    )


def _apply_projection(
    record: ProfessionalReportingLineRecord,
    projection: ReportingLineProjection,
    now: datetime,
) -> None:
    record.organization_id = projection.organization_id
    record.confidence = projection.confidence
    record.review_state = projection.review_state.value
    record.lawful_basis = projection.lawful_basis.value
    record.lawful_basis_reference = projection.lawful_basis_reference
    record.processing_purpose = projection.purpose
    record.current = projection.current
    record.suppressed = projection.suppressed
    record.deleted = projection.deleted
    record.first_observed_at = projection.first_observed_at
    record.last_observed_at = projection.last_observed_at
    record.retention_until = projection.retention_until
    record.updated_at = now

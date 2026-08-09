from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.professional_context.domain import (
    PublicCommunityContext,
    PublicCommunityProjection,
    reconcile_community_context,
)
from cip.modules.professional_context.infrastructure.context_models import (
    ProfessionalCommunityRecord,
    ProfessionalCommunitySnapshotRecord,
)
from cip.modules.professional_context.infrastructure.projection_hydration import (
    community_snapshot,
)
from cip.modules.professional_context.infrastructure.projection_payloads import (
    community_snapshot_digest,
)
from cip.shared.kernel.time import require_aware_utc


def persist_community_context(
    session: Session,
    contexts: Iterable[PublicCommunityContext],
    *,
    now: datetime,
) -> tuple[ProfessionalCommunityRecord, ...]:
    current = require_aware_utc(now, field_name="now")
    grouped: dict[str, list[PublicCommunityContext]] = defaultdict(list)
    for item in contexts:
        grouped[item.context_key].append(item)
    records: list[ProfessionalCommunityRecord] = []
    for context_key, incoming in grouped.items():
        record = session.scalar(
            select(ProfessionalCommunityRecord).where(
                ProfessionalCommunityRecord.context_key == context_key
            )
        )
        if record is None:
            record = _new_record(reconcile_community_context(incoming, now=current), current)
            session.add(record)
            session.flush()
        _insert_snapshots(session, record, incoming, current)
        session.flush()
        history = tuple(
            community_snapshot(item)
            for item in session.scalars(
                select(ProfessionalCommunitySnapshotRecord)
                .where(ProfessionalCommunitySnapshotRecord.context_id == record.id)
                .order_by(ProfessionalCommunitySnapshotRecord.observed_at)
            )
        )
        _apply_projection(record, reconcile_community_context(history, now=current), current)
        records.append(record)
    session.flush()
    return tuple(records)


def _insert_snapshots(
    session: Session,
    record: ProfessionalCommunityRecord,
    incoming: list[PublicCommunityContext],
    now: datetime,
) -> None:
    for item in incoming:
        digest = community_snapshot_digest(item)
        if session.scalar(
            select(ProfessionalCommunitySnapshotRecord.id).where(
                ProfessionalCommunitySnapshotRecord.snapshot_key == digest
            )
        ):
            continue
        session.add(
            ProfessionalCommunitySnapshotRecord(
                id=uuid4(),
                context_id=record.id,
                snapshot_key=digest,
                context_key=item.context_key,
                community_name=item.community_name,
                context_type=item.context_type,
                context_value=item.context_value,
                acquisition_mode=item.acquisition_mode.value,
                authorization_reference=item.authorization_reference,
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
                metadata_only=item.metadata_only,
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
    projection: PublicCommunityProjection,
    now: datetime,
) -> ProfessionalCommunityRecord:
    return ProfessionalCommunityRecord(
        id=uuid4(),
        context_key=projection.context_key,
        community_name=projection.community_name,
        context_type=projection.context_type,
        context_value=projection.context_value,
        acquisition_mode=projection.acquisition_mode.value,
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
    record: ProfessionalCommunityRecord,
    projection: PublicCommunityProjection,
    now: datetime,
) -> None:
    record.community_name = projection.community_name
    record.context_type = projection.context_type
    record.context_value = projection.context_value
    record.acquisition_mode = projection.acquisition_mode.value
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

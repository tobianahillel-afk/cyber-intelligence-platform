from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.professional_context.domain import (
    ProfessionalRoleClaim,
    ProfessionalRoleProjection,
    reconcile_role_claims,
)
from cip.modules.professional_context.infrastructure.projection_hydration import role_snapshot
from cip.modules.professional_context.infrastructure.projection_payloads import role_snapshot_digest
from cip.modules.professional_context.infrastructure.role_models import (
    ProfessionalRoleRecord,
    ProfessionalRoleSnapshotRecord,
)
from cip.shared.kernel.time import require_aware_utc


def persist_professional_roles(
    session: Session,
    claims: Iterable[ProfessionalRoleClaim],
    *,
    now: datetime,
) -> tuple[ProfessionalRoleRecord, ...]:
    current = require_aware_utc(now, field_name="now")
    grouped: dict[str, list[ProfessionalRoleClaim]] = defaultdict(list)
    for claim in claims:
        grouped[claim.claim_key].append(claim)
    records: list[ProfessionalRoleRecord] = []
    for claim_key, incoming in grouped.items():
        record = session.scalar(
            select(ProfessionalRoleRecord).where(ProfessionalRoleRecord.claim_key == claim_key)
        )
        if record is None:
            record = _new_record(reconcile_role_claims(incoming, now=current), current)
            session.add(record)
            session.flush()
        _insert_snapshots(session, record, incoming, current)
        session.flush()
        history = tuple(
            role_snapshot(item)
            for item in session.scalars(
                select(ProfessionalRoleSnapshotRecord)
                .where(ProfessionalRoleSnapshotRecord.role_id == record.id)
                .order_by(ProfessionalRoleSnapshotRecord.observed_at)
            )
        )
        _apply_projection(record, reconcile_role_claims(history, now=current), current)
        records.append(record)
    session.flush()
    return tuple(records)


def _insert_snapshots(
    session: Session,
    record: ProfessionalRoleRecord,
    incoming: list[ProfessionalRoleClaim],
    now: datetime,
) -> None:
    for item in incoming:
        digest = role_snapshot_digest(item)
        if session.scalar(
            select(ProfessionalRoleSnapshotRecord.id).where(
                ProfessionalRoleSnapshotRecord.snapshot_key == digest
            )
        ):
            continue
        session.add(
            ProfessionalRoleSnapshotRecord(
                id=uuid4(),
                role_id=record.id,
                snapshot_key=digest,
                claim_key=item.claim_key,
                person_key=item.person_key,
                source_id=item.source_id,
                source_record_key=item.source_record_key,
                source_url=item.source_url,
                role_title=item.role_title,
                team_name=item.team_name,
                claimed_organization_name=item.claimed_organization_name,
                organization_id=item.organization_id,
                organization_link_status=item.organization_link_status.value,
                claim_type=item.claim_type.value,
                review_state=item.review_state.value,
                observed_at=item.observed_at,
                valid_from=item.valid_from,
                valid_until=item.valid_until,
                expires_at=item.expires_at,
                confidence=item.confidence,
                active=item.active,
                historical_only=item.historical_only,
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


def _new_record(projection: ProfessionalRoleProjection, now: datetime) -> ProfessionalRoleRecord:
    return ProfessionalRoleRecord(
        id=uuid4(),
        claim_key=projection.claim_key,
        person_key=projection.person_key,
        organization_id=projection.organization_id,
        claimed_organization_name=projection.claimed_organization_name,
        role_title=projection.role_title,
        team_name=projection.team_name,
        employment_state=projection.employment_state.value,
        confidence=projection.confidence,
        review_state=projection.review_state.value,
        lawful_basis=projection.lawful_basis.value,
        lawful_basis_reference=projection.lawful_basis_reference,
        processing_purpose=projection.purpose,
        suppressed=projection.suppressed,
        deleted=projection.deleted,
        evidence_count=projection.evidence_count,
        first_observed_at=projection.first_observed_at,
        last_observed_at=projection.last_observed_at,
        retention_until=projection.retention_until,
        created_at=now,
        updated_at=now,
    )


def _apply_projection(
    record: ProfessionalRoleRecord,
    projection: ProfessionalRoleProjection,
    now: datetime,
) -> None:
    record.person_key = projection.person_key
    record.organization_id = projection.organization_id
    record.claimed_organization_name = projection.claimed_organization_name
    record.role_title = projection.role_title
    record.team_name = projection.team_name
    record.employment_state = projection.employment_state.value
    record.confidence = projection.confidence
    record.review_state = projection.review_state.value
    record.lawful_basis = projection.lawful_basis.value
    record.lawful_basis_reference = projection.lawful_basis_reference
    record.processing_purpose = projection.purpose
    record.suppressed = projection.suppressed
    record.deleted = projection.deleted
    record.evidence_count = projection.evidence_count
    record.first_observed_at = projection.first_observed_at
    record.last_observed_at = projection.last_observed_at
    record.retention_until = projection.retention_until
    record.updated_at = now

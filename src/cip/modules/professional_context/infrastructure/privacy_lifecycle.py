from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from cip.modules.data_governance.domain.suppression import (
    SuppressionChannel,
    SuppressionReason,
    create_suppression,
)
from cip.modules.professional_context.infrastructure.contact_models import (
    ProfessionalContactRecord,
    ProfessionalContactSnapshotRecord,
)
from cip.modules.professional_context.infrastructure.context_models import (
    ProfessionalCommunityRecord,
    ProfessionalCommunitySnapshotRecord,
    ProfessionalServiceRelevanceRecord,
)
from cip.modules.professional_context.infrastructure.person_models import (
    ProfessionalPersonRecord,
    ProfessionalPersonSnapshotRecord,
)
from cip.modules.professional_context.infrastructure.privacy_models import (
    ProfessionalDeletionAuditRecord,
)
from cip.modules.professional_context.infrastructure.role_models import (
    ProfessionalReportingLineRecord,
    ProfessionalReportingSnapshotRecord,
    ProfessionalRoleRecord,
    ProfessionalRoleSnapshotRecord,
)
from cip.shared.kernel.time import require_aware_utc


class ProfessionalPersonNotFoundError(LookupError):
    pass


def erase_professional_person(
    session: Session,
    *,
    person_key: str,
    identifier: str,
    channel: SuppressionChannel,
    reason: SuppressionReason,
    pepper: bytes,
    now: datetime,
    minimum_retention_days: int,
    source: str,
    actor: str,
) -> ProfessionalDeletionAuditRecord:
    current = require_aware_utc(now, field_name="now")
    person = session.scalar(
        select(ProfessionalPersonRecord).where(
            ProfessionalPersonRecord.person_key == person_key
        )
    )
    if person is None:
        raise ProfessionalPersonNotFoundError(person_key)
    suppression = create_suppression(
        identifier,
        channel,
        reason,
        pepper=pepper,
        now=current,
        minimum_retention_days=minimum_retention_days,
        source=source,
    )
    _redact_person(session, person, current)
    _redact_roles(session, person_key)
    _redact_reporting(session, person_key)
    _redact_contacts(session, person_key)
    _redact_community(session, person_key)
    _delete_relevance(session, person_key)
    audit = session.scalar(
        select(ProfessionalDeletionAuditRecord).where(
            ProfessionalDeletionAuditRecord.person_id == person.id,
            ProfessionalDeletionAuditRecord.subject_hash == suppression.subject_hash,
            ProfessionalDeletionAuditRecord.channel == channel.value,
        )
    )
    if audit is None:
        audit = ProfessionalDeletionAuditRecord(
            id=uuid4(),
            person_id=person.id,
            subject_hash=suppression.subject_hash,
            channel=channel.value,
            reason=reason.value,
            source=source.strip(),
            actor=actor.strip(),
            requested_at=current,
            applied_at=current,
            suppression_expires_at=suppression.expires_at,
        )
        session.add(audit)
    session.flush()
    return audit


def _redact_person(
    session: Session,
    person: ProfessionalPersonRecord,
    now: datetime,
) -> None:
    person.display_name = None
    person.current = False
    person.suppressed = True
    person.deleted = True
    person.updated_at = now
    for snapshot in session.scalars(
        select(ProfessionalPersonSnapshotRecord).where(
            ProfessionalPersonSnapshotRecord.person_id == person.id
        )
    ):
        snapshot.display_name = None
        snapshot.source_record_key = None
        snapshot.source_url = None
        snapshot.active = False
        snapshot.suppressed = True
        snapshot.deleted = True


def _redact_roles(session: Session, person_key: str) -> None:
    for record in session.scalars(
        select(ProfessionalRoleRecord).where(
            ProfessionalRoleRecord.person_key == person_key
        )
    ):
        record.role_title = None
        record.team_name = None
        record.claimed_organization_name = None
        record.organization_id = None
        record.suppressed = True
        record.deleted = True
    for snapshot in session.scalars(
        select(ProfessionalRoleSnapshotRecord).where(
            ProfessionalRoleSnapshotRecord.person_key == person_key
        )
    ):
        snapshot.source_record_key = None
        snapshot.source_url = None
        snapshot.role_title = None
        snapshot.team_name = None
        snapshot.claimed_organization_name = None
        snapshot.organization_id = None
        snapshot.active = False
        snapshot.suppressed = True
        snapshot.deleted = True


def _redact_reporting(session: Session, person_key: str) -> None:
    predicate = or_(
        ProfessionalReportingLineRecord.subject_person_key == person_key,
        ProfessionalReportingLineRecord.manager_person_key == person_key,
    )
    for record in session.scalars(select(ProfessionalReportingLineRecord).where(predicate)):
        record.organization_id = None
        record.current = False
        record.suppressed = True
        record.deleted = True
    snapshot_predicate = or_(
        ProfessionalReportingSnapshotRecord.subject_person_key == person_key,
        ProfessionalReportingSnapshotRecord.manager_person_key == person_key,
    )
    for snapshot in session.scalars(
        select(ProfessionalReportingSnapshotRecord).where(snapshot_predicate)
    ):
        snapshot.organization_id = None
        snapshot.source_record_key = None
        snapshot.source_url = None
        snapshot.active = False
        snapshot.suppressed = True
        snapshot.deleted = True


def _redact_contacts(session: Session, person_key: str) -> None:
    for record in session.scalars(
        select(ProfessionalContactRecord).where(
            ProfessionalContactRecord.person_key == person_key
        )
    ):
        record.value = None
        record.current = False
        record.suppressed = True
        record.deleted = True
    for snapshot in session.scalars(
        select(ProfessionalContactSnapshotRecord).where(
            ProfessionalContactSnapshotRecord.person_key == person_key
        )
    ):
        snapshot.value = None
        snapshot.source_record_key = None
        snapshot.source_url = None
        snapshot.active = False
        snapshot.suppressed = True
        snapshot.deleted = True


def _redact_community(session: Session, person_key: str) -> None:
    for record in session.scalars(
        select(ProfessionalCommunityRecord).where(
            ProfessionalCommunityRecord.person_key == person_key
        )
    ):
        record.context_value = None
        record.current = False
        record.suppressed = True
        record.deleted = True
    for snapshot in session.scalars(
        select(ProfessionalCommunitySnapshotRecord).where(
            ProfessionalCommunitySnapshotRecord.person_key == person_key
        )
    ):
        snapshot.context_value = None
        snapshot.source_record_key = None
        snapshot.source_url = None
        snapshot.active = False
        snapshot.suppressed = True
        snapshot.deleted = True


def _delete_relevance(session: Session, person_key: str) -> None:
    for record in session.scalars(
        select(ProfessionalServiceRelevanceRecord).where(
            ProfessionalServiceRelevanceRecord.person_key == person_key
        )
    ):
        session.delete(record)

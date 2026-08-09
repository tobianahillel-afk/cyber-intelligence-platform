from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.conditional_integrations.domain import ProviderApprovalDossier
from cip.modules.conditional_integrations.infrastructure.models import (
    ConditionalProviderApprovalRecord,
    ConditionalProviderApprovalRevisionRecord,
)
from cip.modules.conditional_integrations.infrastructure.payloads import (
    dossier_payload,
    dossier_revision_key,
)
from cip.shared.kernel.time import require_aware_utc


def persist_provider_approval(
    session: Session,
    dossier: ProviderApprovalDossier,
    *,
    now: datetime,
) -> ConditionalProviderApprovalRecord:
    current = require_aware_utc(now, field_name="now")
    revision_key = dossier_revision_key(dossier)
    record = session.scalar(
        select(ConditionalProviderApprovalRecord).where(
            ConditionalProviderApprovalRecord.source_id == dossier.source_id
        )
    )
    if record is None:
        record = _new_approval_record(dossier, revision_key, current)
        session.add(record)
        session.flush()
    elif record.provider_kind != dossier.provider_kind.value:
        raise ValueError("provider_kind cannot change for an existing source_id")
    if not _revision_exists(session, revision_key):
        session.add(_new_revision_record(record, dossier, revision_key, current))
    if record.current_revision_key != revision_key:
        _apply_dossier(record, dossier, revision_key, current)
    session.flush()
    return record


def _revision_exists(session: Session, revision_key: str) -> bool:
    return (
        session.scalar(
            select(ConditionalProviderApprovalRevisionRecord.id).where(
                ConditionalProviderApprovalRevisionRecord.revision_key == revision_key
            )
        )
        is not None
    )


def _new_approval_record(
    dossier: ProviderApprovalDossier,
    revision_key: str,
    now: datetime,
) -> ConditionalProviderApprovalRecord:
    payload = dossier_payload(dossier)
    return ConditionalProviderApprovalRecord(
        id=uuid4(),
        current_revision_key=revision_key,
        created_at=now,
        updated_at=now,
        **payload,
    )


def _new_revision_record(
    approval: ConditionalProviderApprovalRecord,
    dossier: ProviderApprovalDossier,
    revision_key: str,
    now: datetime,
) -> ConditionalProviderApprovalRevisionRecord:
    return ConditionalProviderApprovalRevisionRecord(
        id=uuid4(),
        approval_id=approval.id,
        revision_key=revision_key,
        created_at=now,
        **dossier_payload(dossier),
    )


def _apply_dossier(
    record: ConditionalProviderApprovalRecord,
    dossier: ProviderApprovalDossier,
    revision_key: str,
    now: datetime,
) -> None:
    payload = dossier_payload(dossier)
    for field_name, value in payload.items():
        setattr(record, field_name, value)
    record.current_revision_key = revision_key
    record.updated_at = now

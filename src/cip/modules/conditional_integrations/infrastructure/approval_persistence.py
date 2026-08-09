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
    dossier_revision_key,
)
from cip.shared.kernel.time import require_aware_utc


def persist_provider_approval(
    session: Session,
    dossier: ProviderApprovalDossier,
    *,
    actor: str,
    change_reason: str,
    now: datetime,
) -> ConditionalProviderApprovalRecord:
    current = require_aware_utc(now, field_name="now")
    normalized_actor = _required_text(actor, "actor", 200)
    normalized_reason = _required_text(change_reason, "change_reason", 1000)
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
        session.add(
            _new_revision_record(
                record,
                dossier,
                revision_key,
                actor=normalized_actor,
                change_reason=normalized_reason,
                now=current,
            )
        )
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
    return ConditionalProviderApprovalRecord(
        id=uuid4(),
        current_revision_key=revision_key,
        created_at=now,
        updated_at=now,
        **_record_values(dossier),
    )


def _new_revision_record(
    approval: ConditionalProviderApprovalRecord,
    dossier: ProviderApprovalDossier,
    revision_key: str,
    *,
    actor: str,
    change_reason: str,
    now: datetime,
) -> ConditionalProviderApprovalRevisionRecord:
    return ConditionalProviderApprovalRevisionRecord(
        id=uuid4(),
        approval_id=approval.id,
        revision_key=revision_key,
        actor=actor,
        change_reason=change_reason,
        created_at=now,
        **_record_values(dossier),
    )


def _apply_dossier(
    record: ConditionalProviderApprovalRecord,
    dossier: ProviderApprovalDossier,
    revision_key: str,
    now: datetime,
) -> None:
    for field_name, value in _record_values(dossier).items():
        setattr(record, field_name, value)
    record.current_revision_key = revision_key
    record.updated_at = now


def _record_values(dossier: ProviderApprovalDossier) -> dict[str, object]:
    return {
        "source_id": dossier.source_id,
        "provider_kind": dossier.provider_kind.value,
        "access_method": dossier.access_method.value,
        "state": dossier.state.value,
        "authorization_document_reference": dossier.authorization_document_reference,
        "licence_reference": dossier.licence_reference,
        "terms_reference": dossier.terms_reference,
        "terms_state": dossier.terms_state.value,
        "approved_scopes": sorted(dossier.approved_scopes),
        "approved_fields": sorted(dossier.approved_fields),
        "approved_purposes": sorted(dossier.approved_purposes),
        "approved_data_categories": sorted(
            value.value for value in dossier.approved_data_categories
        ),
        "retention_days": dossier.retention_days,
        "automated_collection_allowed": dossier.automated_collection_allowed,
        "account_reference": dossier.account_reference,
        "reviewed_at": dossier.reviewed_at,
        "review_due_at": dossier.review_due_at,
        "expires_at": dossier.expires_at,
        "revoked_at": dossier.revoked_at,
        "paused_reason": dossier.paused_reason,
    }


def _required_text(value: str, field_name: str, maximum: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > maximum:
        raise ValueError(f"{field_name} cannot exceed {maximum} characters")
    return normalized

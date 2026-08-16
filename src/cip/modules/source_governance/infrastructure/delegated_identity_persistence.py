from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.source_governance.domain.accounts import (
    SourceAccount,
    SourceAccountAuthMode,
    SourceAccountStatus,
)
from cip.modules.source_governance.domain.delegated_browser_identity import (
    DelegatedBrowserIdentity,
    DelegatedOwnerKind,
)
from cip.modules.source_governance.infrastructure.delegated_identity_models import (
    DelegatedBrowserIdentityAuditRecord,
    DelegatedBrowserIdentityRecord,
)
from cip.shared.kernel.time import require_aware_utc


def insert_delegated_identity(
    session: Session,
    identity: DelegatedBrowserIdentity,
    *,
    now: datetime,
) -> None:
    session.add(_new_record(identity, now))
    session.flush()


def save_delegated_identity(
    session: Session,
    identity: DelegatedBrowserIdentity,
    *,
    now: datetime,
) -> bool:
    record = session.get(DelegatedBrowserIdentityRecord, identity.id)
    if record is None:
        return False
    replacement = _new_record(identity, now)
    for column in DelegatedBrowserIdentityRecord.__table__.columns:
        if column.name == "id":
            continue
        setattr(record, column.name, getattr(replacement, column.name))
    session.flush()
    return True


def load_delegated_identity(
    session: Session,
    identity_id: UUID,
) -> DelegatedBrowserIdentity | None:
    record = session.get(DelegatedBrowserIdentityRecord, identity_id)
    return None if record is None else _to_domain(record)


def list_delegated_identities_for_owner(
    session: Session,
    *,
    tenant_id: UUID,
    owner_kind: DelegatedOwnerKind,
    owner_subject_id: str,
) -> tuple[DelegatedBrowserIdentity, ...]:
    records = session.scalars(
        select(DelegatedBrowserIdentityRecord)
        .where(
            DelegatedBrowserIdentityRecord.tenant_id == tenant_id,
            DelegatedBrowserIdentityRecord.owner_kind == owner_kind.value,
            DelegatedBrowserIdentityRecord.owner_subject_id == owner_subject_id,
        )
        .order_by(
            DelegatedBrowserIdentityRecord.source_id,
            DelegatedBrowserIdentityRecord.created_at,
            DelegatedBrowserIdentityRecord.id,
        )
    ).all()
    return tuple(_to_domain(record) for record in records)


def append_delegated_identity_audit(
    session: Session,
    identity: DelegatedBrowserIdentity,
    *,
    actor_kind: DelegatedOwnerKind,
    actor_subject_id: str,
    event_type: str,
    at: datetime,
) -> None:
    session.add(
        DelegatedBrowserIdentityAuditRecord(
            id=uuid4(),
            identity_id=identity.id,
            tenant_id=identity.tenant_id,
            event_type=event_type,
            actor_kind=actor_kind.value,
            actor_subject_id=actor_subject_id,
            reference_version=identity.reference_version,
            occurred_at=require_aware_utc(at, field_name="at"),
        )
    )
    session.flush()


def list_delegated_identity_audit_records(
    session: Session,
    identity_id: UUID,
) -> tuple[DelegatedBrowserIdentityAuditRecord, ...]:
    return tuple(
        session.scalars(
            select(DelegatedBrowserIdentityAuditRecord)
            .where(DelegatedBrowserIdentityAuditRecord.identity_id == identity_id)
            .order_by(
                DelegatedBrowserIdentityAuditRecord.occurred_at,
                DelegatedBrowserIdentityAuditRecord.id,
            )
        ).all()
    )


def new_identity_record_exists(session: Session, identity_id: UUID) -> bool:
    return session.get(DelegatedBrowserIdentityRecord, identity_id) is not None


def audit_record_time(record: DelegatedBrowserIdentityAuditRecord) -> datetime:
    return _coerce_utc(record.occurred_at)


def _new_record(
    identity: DelegatedBrowserIdentity,
    now: datetime,
) -> DelegatedBrowserIdentityRecord:
    return DelegatedBrowserIdentityRecord(
        id=identity.id,
        source_id=identity.account.source_id,
        external_reference=identity.account.external_reference,
        auth_mode=identity.account.auth_mode.value,
        account_status=identity.account.status.value,
        authorization_document_reference=identity.account.authorization_document_reference,
        approved_purposes=sorted(identity.account.approved_purposes),
        tenant_id=identity.tenant_id,
        owner_kind=identity.owner_kind.value,
        owner_subject_id=identity.owner_subject_id,
        purpose=identity.purpose,
        approved_scopes=sorted(identity.approved_scopes),
        secret_reference=identity.secret_reference,
        session_reference=identity.session_reference,
        created_at=identity.created_at,
        verified_at=identity.account.verified_at,
        account_expires_at=identity.account.expires_at,
        last_used_at=identity.account.last_used_at,
        authorized_at=identity.authorized_at,
        reviewed_at=identity.reviewed_at,
        renewed_at=identity.renewed_at,
        reference_rotated_at=identity.reference_rotated_at,
        revoked_at=identity.revoked_at,
        deleted_at=identity.deleted_at,
        session_expires_at=identity.session_expires_at,
        reference_version=identity.reference_version,
        updated_at=require_aware_utc(now, field_name="now"),
    )


def _to_domain(record: DelegatedBrowserIdentityRecord) -> DelegatedBrowserIdentity:
    created = _coerce_utc(record.created_at)
    account = SourceAccount(
        id=record.id,
        source_id=record.source_id,
        external_reference=record.external_reference,
        auth_mode=SourceAccountAuthMode(record.auth_mode),
        status=SourceAccountStatus(record.account_status),
        authorization_document_reference=record.authorization_document_reference,
        approved_purposes=frozenset(record.approved_purposes),
        created_at=created,
        verified_at=_optional_utc(record.verified_at),
        expires_at=_optional_utc(record.account_expires_at),
        last_used_at=_optional_utc(record.last_used_at),
    )
    return DelegatedBrowserIdentity(
        account=account,
        tenant_id=record.tenant_id,
        owner_kind=DelegatedOwnerKind(record.owner_kind),
        owner_subject_id=record.owner_subject_id,
        purpose=record.purpose,
        approved_scopes=frozenset(record.approved_scopes),
        created_at=created,
        authorized_at=_optional_utc(record.authorized_at),
        reviewed_at=_optional_utc(record.reviewed_at),
        renewed_at=_optional_utc(record.renewed_at),
        reference_rotated_at=_optional_utc(record.reference_rotated_at),
        revoked_at=_optional_utc(record.revoked_at),
        deleted_at=_optional_utc(record.deleted_at),
        session_expires_at=_optional_utc(record.session_expires_at),
        reference_version=record.reference_version,
        secret_reference=record.secret_reference,
        session_reference=record.session_reference,
    )


def _optional_utc(value: datetime | None) -> datetime | None:
    return None if value is None else _coerce_utc(value)


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

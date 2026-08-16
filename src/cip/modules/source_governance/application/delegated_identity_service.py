from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.provider_onboarding.application.secrets import SecretReferenceResolver
from cip.modules.provider_onboarding.domain.models import SecretReference
from cip.modules.source_governance.domain.accounts import (
    SourceAccount,
    SourceAccountAuthMode,
    SourceAccountStatus,
)
from cip.modules.source_governance.domain.delegated_browser_identity import (
    DelegatedBrowserIdentity,
    DelegatedExecutionRequest,
    DelegatedOwnerKind,
)
from cip.modules.source_governance.infrastructure.delegated_identity_models import (
    DelegatedBrowserIdentityAuditRecord,
    DelegatedBrowserIdentityRecord,
)
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.shared.kernel.time import require_aware_utc


class DelegatedIdentityAuditEvent(StrEnum):
    REGISTERED = "registered"
    AUTHORIZED = "authorized"
    SECRET_REFERENCE_UPDATED = "secret_reference_updated"
    SESSION_REFERENCE_UPDATED = "session_reference_updated"
    RENEWED = "renewed"
    USED = "used"
    REVOKED = "revoked"
    DELETED = "deleted"


@dataclass(frozen=True, slots=True)
class DelegatedOperatorContext:
    tenant_id: UUID
    owner_kind: DelegatedOwnerKind
    owner_subject_id: str

    def __post_init__(self) -> None:
        if not self.owner_subject_id.strip() or len(self.owner_subject_id) > 200:
            raise ValueError("operator owner_subject_id is invalid")


@dataclass(frozen=True, slots=True)
class DelegatedIdentityView:
    id: UUID
    source_id: str
    provider_account_identifier: str
    auth_mode: SourceAccountAuthMode
    status: SourceAccountStatus
    tenant_id: UUID
    owner_kind: DelegatedOwnerKind
    owner_subject_id: str
    purpose: str
    approved_scopes: tuple[str, ...]
    authorization_document_reference: str | None
    created_at: datetime
    authorized_at: datetime | None
    reviewed_at: datetime | None
    expires_at: datetime | None
    last_used_at: datetime | None
    renewed_at: datetime | None
    reference_rotated_at: datetime | None
    revoked_at: datetime | None
    deleted_at: datetime | None
    session_expires_at: datetime | None
    reference_version: int
    has_secret_reference: bool
    has_session_reference: bool


@dataclass(frozen=True, slots=True)
class DelegatedIdentityAuditView:
    event_type: DelegatedIdentityAuditEvent
    actor_kind: DelegatedOwnerKind
    actor_subject_id: str
    reference_version: int
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class DelegatedIdentityExecutionGrant:
    identity_id: UUID
    source_id: str
    tenant_id: UUID
    purpose: str
    approved_scopes: tuple[str, ...]
    secret_reference: str | None = None
    session_reference: str | None = None

    def __repr__(self) -> str:
        return (
            "DelegatedIdentityExecutionGrant("
            f"identity_id={self.identity_id!r}, source_id={self.source_id!r}, "
            f"tenant_id={self.tenant_id!r}, purpose={self.purpose!r}, "
            f"approved_scopes={self.approved_scopes!r}, "
            f"has_secret_reference={self.secret_reference is not None!r}, "
            f"has_session_reference={self.session_reference is not None!r})"
        )


class DelegatedIdentityNotFoundError(LookupError):
    pass


class DelegatedIdentityAccessDeniedError(RuntimeError):
    pass


class DelegatedReferenceUnavailableError(RuntimeError):
    pass


def register_delegated_identity(
    session: Session,
    identity: DelegatedBrowserIdentity,
    *,
    actor: DelegatedOperatorContext,
    now: datetime,
) -> DelegatedIdentityView:
    changed_at = require_aware_utc(now, field_name="now")
    _assert_operator(identity, actor)
    if identity.account.status is not SourceAccountStatus.PENDING_VERIFICATION:
        raise ValueError("new delegated identity must start pending verification")
    if session.get(SourceRecord, identity.account.source_id) is None:
        raise ValueError("delegated identity source must exist")
    if session.get(DelegatedBrowserIdentityRecord, identity.id) is not None:
        raise ValueError("delegated identity already exists")
    record = _new_record(identity, changed_at)
    session.add(record)
    _audit(session, identity, actor, DelegatedIdentityAuditEvent.REGISTERED, changed_at)
    session.flush()
    return _view(identity)


def get_delegated_identity(
    session: Session,
    identity_id: UUID,
    *,
    actor: DelegatedOperatorContext,
) -> DelegatedIdentityView:
    identity = _get_domain(session, identity_id)
    _assert_operator(identity, actor)
    return _view(identity)


def list_delegated_identities(
    session: Session,
    *,
    actor: DelegatedOperatorContext,
) -> tuple[DelegatedIdentityView, ...]:
    records = session.scalars(
        select(DelegatedBrowserIdentityRecord)
        .where(
            DelegatedBrowserIdentityRecord.tenant_id == actor.tenant_id,
            DelegatedBrowserIdentityRecord.owner_kind == actor.owner_kind.value,
            DelegatedBrowserIdentityRecord.owner_subject_id == actor.owner_subject_id,
        )
        .order_by(
            DelegatedBrowserIdentityRecord.source_id,
            DelegatedBrowserIdentityRecord.created_at,
            DelegatedBrowserIdentityRecord.id,
        )
    ).all()
    return tuple(_view(_to_domain(record)) for record in records)


def list_delegated_identity_audit(
    session: Session,
    identity_id: UUID,
    *,
    actor: DelegatedOperatorContext,
) -> tuple[DelegatedIdentityAuditView, ...]:
    identity = _get_domain(session, identity_id)
    _assert_operator(identity, actor)
    records = session.scalars(
        select(DelegatedBrowserIdentityAuditRecord)
        .where(DelegatedBrowserIdentityAuditRecord.identity_id == identity_id)
        .order_by(
            DelegatedBrowserIdentityAuditRecord.occurred_at,
            DelegatedBrowserIdentityAuditRecord.id,
        )
    ).all()
    return tuple(_audit_view(record) for record in records)


def authorize_delegated_identity(
    session: Session,
    identity_id: UUID,
    *,
    actor: DelegatedOperatorContext,
    reviewed_at: datetime,
) -> DelegatedIdentityView:
    identity = _get_owned(session, identity_id, actor)
    updated = identity.authorize(reviewed_at=reviewed_at)
    _save(session, updated, now=reviewed_at)
    _audit(session, updated, actor, DelegatedIdentityAuditEvent.AUTHORIZED, reviewed_at)
    return _view(updated)


def attach_delegated_secret_reference(
    session: Session,
    identity_id: UUID,
    reference: str,
    *,
    actor: DelegatedOperatorContext,
    resolver: SecretReferenceResolver,
    now: datetime,
) -> DelegatedIdentityView:
    normalized = _available_reference(reference, resolver)
    identity = _get_owned(session, identity_id, actor)
    updated = identity.attach_secret_reference(normalized, at=now)
    _save(session, updated, now=now)
    _audit(
        session,
        updated,
        actor,
        DelegatedIdentityAuditEvent.SECRET_REFERENCE_UPDATED,
        now,
    )
    return _view(updated)


def attach_delegated_session_reference(
    session: Session,
    identity_id: UUID,
    reference: str,
    *,
    actor: DelegatedOperatorContext,
    resolver: SecretReferenceResolver,
    now: datetime,
    expires_at: datetime | None = None,
) -> DelegatedIdentityView:
    normalized = _available_reference(reference, resolver)
    identity = _get_owned(session, identity_id, actor)
    updated = identity.attach_session_reference(
        normalized,
        at=now,
        expires_at=expires_at,
    )
    _save(session, updated, now=now)
    _audit(
        session,
        updated,
        actor,
        DelegatedIdentityAuditEvent.SESSION_REFERENCE_UPDATED,
        now,
    )
    return _view(updated)


def renew_delegated_identity(
    session: Session,
    identity_id: UUID,
    *,
    actor: DelegatedOperatorContext,
    expires_at: datetime,
    now: datetime,
) -> DelegatedIdentityView:
    identity = _get_owned(session, identity_id, actor)
    updated = identity.renew(expires_at=expires_at, at=now)
    _save(session, updated, now=now)
    _audit(session, updated, actor, DelegatedIdentityAuditEvent.RENEWED, now)
    return _view(updated)


def revoke_delegated_identity(
    session: Session,
    identity_id: UUID,
    *,
    actor: DelegatedOperatorContext,
    now: datetime,
) -> DelegatedIdentityView:
    identity = _get_owned(session, identity_id, actor)
    updated = identity.revoke(at=now)
    _save(session, updated, now=now)
    _audit(session, updated, actor, DelegatedIdentityAuditEvent.REVOKED, now)
    return _view(updated)


def delete_delegated_identity(
    session: Session,
    identity_id: UUID,
    *,
    actor: DelegatedOperatorContext,
    now: datetime,
) -> DelegatedIdentityView:
    identity = _get_owned(session, identity_id, actor)
    updated = identity.delete(at=now)
    _save(session, updated, now=now)
    _audit(session, updated, actor, DelegatedIdentityAuditEvent.DELETED, now)
    return _view(updated)


def issue_delegated_execution_grant(
    session: Session,
    identity_id: UUID,
    request: DelegatedExecutionRequest,
    *,
    resolver: SecretReferenceResolver,
    now: datetime,
) -> DelegatedIdentityExecutionGrant:
    identity = _get_domain(session, identity_id)
    decision = identity.evaluate_execution(request, now=now)
    if not decision.allowed:
        raise DelegatedIdentityAccessDeniedError(decision.reason.value)
    secret = _required_available(identity.secret_reference, request.require_secret_reference, resolver)
    browser_session = _required_available(
        identity.session_reference,
        request.require_session_reference,
        resolver,
    )
    used = identity.mark_used(at=now)
    _save(session, used, now=now)
    actor = DelegatedOperatorContext(
        tenant_id=request.tenant_id,
        owner_kind=request.owner_kind,
        owner_subject_id=request.owner_subject_id,
    )
    _audit(session, used, actor, DelegatedIdentityAuditEvent.USED, now)
    return DelegatedIdentityExecutionGrant(
        identity_id=used.id,
        source_id=used.account.source_id,
        tenant_id=used.tenant_id,
        purpose=used.purpose,
        approved_scopes=tuple(sorted(used.approved_scopes)),
        secret_reference=secret,
        session_reference=browser_session,
    )


def _required_available(
    reference: str | None,
    required: bool,
    resolver: SecretReferenceResolver,
) -> str | None:
    if not required:
        return reference
    if reference is None:
        raise DelegatedReferenceUnavailableError("required delegated reference is missing")
    return _available_reference(reference, resolver)


def _available_reference(reference: str, resolver: SecretReferenceResolver) -> str:
    parsed = SecretReference(reference)
    if not resolver.is_available(parsed):
        raise DelegatedReferenceUnavailableError("delegated reference is unavailable")
    return parsed.value


def _get_owned(
    session: Session,
    identity_id: UUID,
    actor: DelegatedOperatorContext,
) -> DelegatedBrowserIdentity:
    identity = _get_domain(session, identity_id)
    _assert_operator(identity, actor)
    return identity


def _get_domain(session: Session, identity_id: UUID) -> DelegatedBrowserIdentity:
    record = session.get(DelegatedBrowserIdentityRecord, identity_id)
    if record is None:
        raise DelegatedIdentityNotFoundError(str(identity_id))
    return _to_domain(record)


def _assert_operator(
    identity: DelegatedBrowserIdentity,
    actor: DelegatedOperatorContext,
) -> None:
    if (
        identity.tenant_id != actor.tenant_id
        or identity.owner_kind is not actor.owner_kind
        or identity.owner_subject_id != actor.owner_subject_id
    ):
        raise DelegatedIdentityAccessDeniedError("delegated identity owner mismatch")


def _new_record(identity: DelegatedBrowserIdentity, now: datetime) -> DelegatedBrowserIdentityRecord:
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


def _save(session: Session, identity: DelegatedBrowserIdentity, *, now: datetime) -> None:
    record = session.get(DelegatedBrowserIdentityRecord, identity.id)
    if record is None:
        raise DelegatedIdentityNotFoundError(str(identity.id))
    replacement = _new_record(identity, now)
    for column in DelegatedBrowserIdentityRecord.__table__.columns:
        if column.name == "id":
            continue
        setattr(record, column.name, getattr(replacement, column.name))
    session.flush()


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


def _view(identity: DelegatedBrowserIdentity) -> DelegatedIdentityView:
    return DelegatedIdentityView(
        id=identity.id,
        source_id=identity.account.source_id,
        provider_account_identifier=identity.account.external_reference,
        auth_mode=identity.account.auth_mode,
        status=identity.account.status,
        tenant_id=identity.tenant_id,
        owner_kind=identity.owner_kind,
        owner_subject_id=identity.owner_subject_id,
        purpose=identity.purpose,
        approved_scopes=tuple(sorted(identity.approved_scopes)),
        authorization_document_reference=identity.account.authorization_document_reference,
        created_at=identity.created_at,
        authorized_at=identity.authorized_at,
        reviewed_at=identity.reviewed_at,
        expires_at=identity.account.expires_at,
        last_used_at=identity.account.last_used_at,
        renewed_at=identity.renewed_at,
        reference_rotated_at=identity.reference_rotated_at,
        revoked_at=identity.revoked_at,
        deleted_at=identity.deleted_at,
        session_expires_at=identity.session_expires_at,
        reference_version=identity.reference_version,
        has_secret_reference=identity.secret_reference is not None,
        has_session_reference=identity.session_reference is not None,
    )


def _audit(
    session: Session,
    identity: DelegatedBrowserIdentity,
    actor: DelegatedOperatorContext,
    event: DelegatedIdentityAuditEvent,
    at: datetime,
) -> None:
    session.add(
        DelegatedBrowserIdentityAuditRecord(
            id=uuid4(),
            identity_id=identity.id,
            tenant_id=identity.tenant_id,
            event_type=event.value,
            actor_kind=actor.owner_kind.value,
            actor_subject_id=actor.owner_subject_id,
            reference_version=identity.reference_version,
            occurred_at=require_aware_utc(at, field_name="at"),
        )
    )
    session.flush()


def _audit_view(record: DelegatedBrowserIdentityAuditRecord) -> DelegatedIdentityAuditView:
    return DelegatedIdentityAuditView(
        event_type=DelegatedIdentityAuditEvent(record.event_type),
        actor_kind=DelegatedOwnerKind(record.actor_kind),
        actor_subject_id=record.actor_subject_id,
        reference_version=record.reference_version,
        occurred_at=_coerce_utc(record.occurred_at),
    )


def _optional_utc(value: datetime | None) -> datetime | None:
    return None if value is None else _coerce_utc(value)


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

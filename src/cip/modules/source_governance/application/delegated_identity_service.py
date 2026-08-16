from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy.orm import Session

from cip.modules.provider_onboarding.application.secrets import SecretReferenceResolver
from cip.modules.provider_onboarding.domain.models import SecretReference
from cip.modules.source_governance.domain.accounts import (
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
)
from cip.modules.source_governance.infrastructure.delegated_identity_persistence import (
    append_delegated_identity_audit,
    audit_record_time,
    insert_delegated_identity,
    list_delegated_identities_for_owner,
    list_delegated_identity_audit_records,
    load_delegated_identity,
    new_identity_record_exists,
    save_delegated_identity,
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
    if new_identity_record_exists(session, identity.id):
        raise ValueError("delegated identity already exists")
    insert_delegated_identity(session, identity, now=changed_at)
    _audit(session, identity, actor, DelegatedIdentityAuditEvent.REGISTERED, changed_at)
    return _view(identity)


def get_delegated_identity(
    session: Session,
    identity_id: UUID,
    *,
    actor: DelegatedOperatorContext,
) -> DelegatedIdentityView:
    return _view(_get_owned(session, identity_id, actor))


def list_delegated_identities(
    session: Session,
    *,
    actor: DelegatedOperatorContext,
) -> tuple[DelegatedIdentityView, ...]:
    identities = list_delegated_identities_for_owner(
        session,
        tenant_id=actor.tenant_id,
        owner_kind=actor.owner_kind,
        owner_subject_id=actor.owner_subject_id,
    )
    return tuple(_view(identity) for identity in identities)


def list_delegated_identity_audit(
    session: Session,
    identity_id: UUID,
    *,
    actor: DelegatedOperatorContext,
) -> tuple[DelegatedIdentityAuditView, ...]:
    _get_owned(session, identity_id, actor)
    records = list_delegated_identity_audit_records(session, identity_id)
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
    _persist_change(session, updated, actor, DelegatedIdentityAuditEvent.AUTHORIZED, reviewed_at)
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
    _persist_change(
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
    updated = identity.attach_session_reference(normalized, at=now, expires_at=expires_at)
    _persist_change(
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
    _persist_change(session, updated, actor, DelegatedIdentityAuditEvent.RENEWED, now)
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
    _persist_change(session, updated, actor, DelegatedIdentityAuditEvent.REVOKED, now)
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
    _persist_change(session, updated, actor, DelegatedIdentityAuditEvent.DELETED, now)
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
    actor = DelegatedOperatorContext(
        tenant_id=request.tenant_id,
        owner_kind=request.owner_kind,
        owner_subject_id=request.owner_subject_id,
    )
    _persist_change(session, used, actor, DelegatedIdentityAuditEvent.USED, now)
    return DelegatedIdentityExecutionGrant(
        identity_id=used.id,
        source_id=used.account.source_id,
        tenant_id=used.tenant_id,
        purpose=used.purpose,
        approved_scopes=tuple(sorted(used.approved_scopes)),
        secret_reference=secret,
        session_reference=browser_session,
    )


def _persist_change(
    session: Session,
    identity: DelegatedBrowserIdentity,
    actor: DelegatedOperatorContext,
    event: DelegatedIdentityAuditEvent,
    at: datetime,
) -> None:
    if not save_delegated_identity(session, identity, now=at):
        raise DelegatedIdentityNotFoundError(str(identity.id))
    _audit(session, identity, actor, event, at)


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
    identity = load_delegated_identity(session, identity_id)
    if identity is None:
        raise DelegatedIdentityNotFoundError(str(identity_id))
    return identity


def _assert_operator(identity: DelegatedBrowserIdentity, actor: DelegatedOperatorContext) -> None:
    if (
        identity.tenant_id != actor.tenant_id
        or identity.owner_kind is not actor.owner_kind
        or identity.owner_subject_id != actor.owner_subject_id
    ):
        raise DelegatedIdentityAccessDeniedError("delegated identity owner mismatch")


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
    append_delegated_identity_audit(
        session,
        identity,
        actor_kind=actor.owner_kind,
        actor_subject_id=actor.owner_subject_id,
        event_type=event.value,
        at=at,
    )


def _audit_view(record: DelegatedBrowserIdentityAuditRecord) -> DelegatedIdentityAuditView:
    return DelegatedIdentityAuditView(
        event_type=DelegatedIdentityAuditEvent(record.event_type),
        actor_kind=DelegatedOwnerKind(record.actor_kind),
        actor_subject_id=record.actor_subject_id,
        reference_version=record.reference_version,
        occurred_at=audit_record_time(record),
    )

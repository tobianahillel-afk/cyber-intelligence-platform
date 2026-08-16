from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from cip.modules.source_governance.domain.accounts import (
    AccountDecisionReason,
    SourceAccount,
    SourceAccountStatus,
)
from cip.shared.kernel.time import require_aware_utc


class DelegatedOwnerKind(StrEnum):
    USER = "user"
    SERVICE_PRINCIPAL = "service_principal"
    DEPLOYMENT_SERVICE = "deployment_service"


class DelegatedIdentityDecisionReason(StrEnum):
    ALLOWED = "allowed"
    TENANT_MISMATCH = "tenant_mismatch"
    OWNER_MISMATCH = "owner_mismatch"
    SOURCE_MISMATCH = "source_mismatch"
    PURPOSE_MISMATCH = "purpose_mismatch"
    SCOPE_MISMATCH = "scope_mismatch"
    ACCOUNT_NOT_ACTIVE = "account_not_active"
    ACCOUNT_EXPIRED = "account_expired"
    AUTHORIZATION_DOCUMENT_MISSING = "authorization_document_missing"
    SECRET_REFERENCE_REQUIRED = "secret_reference_required"
    SESSION_REFERENCE_REQUIRED = "session_reference_required"
    SESSION_EXPIRED = "session_expired"
    REVOKED = "revoked"
    DELETED = "deleted"


@dataclass(frozen=True, slots=True)
class DelegatedExecutionRequest:
    tenant_id: UUID
    owner_kind: DelegatedOwnerKind
    owner_subject_id: str
    source_id: str
    purpose: str
    required_scopes: frozenset[str] = field(default_factory=frozenset)
    require_secret_reference: bool = False
    require_session_reference: bool = False

    def __post_init__(self) -> None:
        _bounded_required(self.owner_subject_id, "owner_subject_id", 200)
        _bounded_required(self.source_id, "source_id", 64)
        _bounded_required(self.purpose, "purpose", 200)
        _validate_scopes(self.required_scopes)


@dataclass(frozen=True, slots=True)
class DelegatedIdentityUseDecision:
    allowed: bool
    reason: DelegatedIdentityDecisionReason


@dataclass(frozen=True, slots=True)
class DelegatedBrowserIdentity:
    account: SourceAccount
    tenant_id: UUID
    owner_kind: DelegatedOwnerKind
    owner_subject_id: str
    purpose: str
    approved_scopes: frozenset[str]
    created_at: datetime
    authorized_at: datetime | None = None
    reviewed_at: datetime | None = None
    renewed_at: datetime | None = None
    reference_rotated_at: datetime | None = None
    revoked_at: datetime | None = None
    deleted_at: datetime | None = None
    session_expires_at: datetime | None = None
    reference_version: int = 0
    secret_reference: str | None = field(default=None, repr=False)
    session_reference: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        _bounded_required(self.owner_subject_id, "owner_subject_id", 200)
        _bounded_required(self.purpose, "purpose", 200)
        _validate_scopes(self.approved_scopes)
        created_at = require_aware_utc(self.created_at, field_name="created_at")
        object.__setattr__(self, "created_at", created_at)
        for field_name in (
            "authorized_at",
            "reviewed_at",
            "renewed_at",
            "reference_rotated_at",
            "revoked_at",
            "deleted_at",
            "session_expires_at",
        ):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    require_aware_utc(value, field_name=field_name),
                )
        if self.account.created_at != created_at:
            raise ValueError("delegated identity and source account creation time must match")
        if self.purpose not in self.account.approved_purposes:
            raise ValueError("delegated identity purpose must be approved by source account")
        if self.reference_version < 0:
            raise ValueError("reference_version cannot be negative")
        _optional_reference(self.secret_reference, "secret_reference")
        _optional_reference(self.session_reference, "session_reference")
        if self.session_expires_at is not None and self.session_reference is None:
            raise ValueError("session_expires_at requires a session reference")
        if self.authorized_at is not None and self.reviewed_at is None:
            raise ValueError("authorized identity requires reviewed_at")
        if self.deleted_at is not None and (
            self.secret_reference is not None or self.session_reference is not None
        ):
            raise ValueError("deleted identity cannot retain secret/session references")
        if self.revoked_at is not None and self.account.status is not SourceAccountStatus.REVOKED:
            raise ValueError("revoked identity requires revoked source account status")

    @property
    def id(self) -> UUID:
        return self.account.id

    def evaluate_execution(
        self,
        request: DelegatedExecutionRequest,
        *,
        now: datetime,
    ) -> DelegatedIdentityUseDecision:
        current = require_aware_utc(now, field_name="now")
        mismatch = self._ownership_mismatch(request)
        if mismatch is not None:
            return DelegatedIdentityUseDecision(False, mismatch)
        if self.deleted_at is not None:
            return DelegatedIdentityUseDecision(False, DelegatedIdentityDecisionReason.DELETED)
        if self.revoked_at is not None or self.account.status is SourceAccountStatus.REVOKED:
            return DelegatedIdentityUseDecision(False, DelegatedIdentityDecisionReason.REVOKED)
        account_decision = self.account.evaluate_use(self.purpose, now=current)
        mapped = _map_account_decision(account_decision.reason)
        if mapped is not DelegatedIdentityDecisionReason.ALLOWED:
            return DelegatedIdentityUseDecision(False, mapped)
        if not request.required_scopes.issubset(self.approved_scopes):
            return DelegatedIdentityUseDecision(
                False,
                DelegatedIdentityDecisionReason.SCOPE_MISMATCH,
            )
        if request.require_secret_reference and self.secret_reference is None:
            return DelegatedIdentityUseDecision(
                False,
                DelegatedIdentityDecisionReason.SECRET_REFERENCE_REQUIRED,
            )
        if request.require_session_reference and self.session_reference is None:
            return DelegatedIdentityUseDecision(
                False,
                DelegatedIdentityDecisionReason.SESSION_REFERENCE_REQUIRED,
            )
        if self.session_expires_at is not None and self.session_expires_at <= current:
            return DelegatedIdentityUseDecision(
                False,
                DelegatedIdentityDecisionReason.SESSION_EXPIRED,
            )
        return DelegatedIdentityUseDecision(True, DelegatedIdentityDecisionReason.ALLOWED)

    def authorize(self, *, reviewed_at: datetime) -> DelegatedBrowserIdentity:
        reviewed = require_aware_utc(reviewed_at, field_name="reviewed_at")
        account = self.account.transition(
            SourceAccountStatus.ACTIVE,
            at=reviewed,
            verified=True,
        )
        return replace(
            self,
            account=account,
            authorized_at=reviewed,
            reviewed_at=reviewed,
        )

    def attach_secret_reference(
        self,
        reference: str,
        *,
        at: datetime,
    ) -> DelegatedBrowserIdentity:
        return self._rotate_reference(secret_reference=reference, at=at)

    def attach_session_reference(
        self,
        reference: str,
        *,
        at: datetime,
        expires_at: datetime | None = None,
    ) -> DelegatedBrowserIdentity:
        session_expiry = _optional_time(expires_at, "expires_at")
        return self._rotate_reference(
            session_reference=reference,
            session_expires_at=session_expiry,
            at=at,
        )

    def renew(self, *, expires_at: datetime, at: datetime) -> DelegatedBrowserIdentity:
        renewal = require_aware_utc(at, field_name="at")
        expiry = require_aware_utc(expires_at, field_name="expires_at")
        if expiry <= renewal:
            raise ValueError("renewed expiry must follow renewal time")
        account = replace(self.account, expires_at=expiry)
        return replace(self, account=account, renewed_at=renewal)

    def revoke(self, *, at: datetime) -> DelegatedBrowserIdentity:
        revoked = require_aware_utc(at, field_name="at")
        if self.deleted_at is not None:
            raise ValueError("deleted identity cannot be revoked")
        if self.account.status is SourceAccountStatus.REVOKED:
            return replace(self, revoked_at=self.revoked_at or revoked)
        account = self.account.transition(SourceAccountStatus.REVOKED, at=revoked)
        return replace(self, account=account, revoked_at=revoked)

    def delete(self, *, at: datetime) -> DelegatedBrowserIdentity:
        deleted = require_aware_utc(at, field_name="at")
        if self.deleted_at is not None:
            return self
        revoked = self if self.account.status is SourceAccountStatus.REVOKED else self.revoke(at=deleted)
        return replace(
            revoked,
            secret_reference=None,
            session_reference=None,
            session_expires_at=None,
            deleted_at=deleted,
        )

    def mark_used(self, *, at: datetime) -> DelegatedBrowserIdentity:
        used = require_aware_utc(at, field_name="at")
        return replace(self, account=replace(self.account, last_used_at=used))

    def _ownership_mismatch(
        self,
        request: DelegatedExecutionRequest,
    ) -> DelegatedIdentityDecisionReason | None:
        if request.tenant_id != self.tenant_id:
            return DelegatedIdentityDecisionReason.TENANT_MISMATCH
        if (
            request.owner_kind is not self.owner_kind
            or request.owner_subject_id != self.owner_subject_id
        ):
            return DelegatedIdentityDecisionReason.OWNER_MISMATCH
        if request.source_id != self.account.source_id:
            return DelegatedIdentityDecisionReason.SOURCE_MISMATCH
        if request.purpose != self.purpose:
            return DelegatedIdentityDecisionReason.PURPOSE_MISMATCH
        return None

    def _rotate_reference(
        self,
        *,
        at: datetime,
        secret_reference: str | None = None,
        session_reference: str | None = None,
        session_expires_at: datetime | None = None,
    ) -> DelegatedBrowserIdentity:
        rotated = require_aware_utc(at, field_name="at")
        if self.deleted_at is not None or self.revoked_at is not None:
            raise ValueError("revoked/deleted identity references cannot be rotated")
        secret = self.secret_reference if secret_reference is None else secret_reference
        session = self.session_reference if session_reference is None else session_reference
        _optional_reference(secret, "secret_reference")
        _optional_reference(session, "session_reference")
        return replace(
            self,
            secret_reference=secret,
            session_reference=session,
            session_expires_at=(
                self.session_expires_at
                if session_reference is None
                else session_expires_at
            ),
            reference_rotated_at=rotated,
            reference_version=self.reference_version + 1,
        )


def _map_account_decision(reason: AccountDecisionReason) -> DelegatedIdentityDecisionReason:
    mapping = {
        AccountDecisionReason.ALLOWED: DelegatedIdentityDecisionReason.ALLOWED,
        AccountDecisionReason.NOT_ACTIVE: DelegatedIdentityDecisionReason.ACCOUNT_NOT_ACTIVE,
        AccountDecisionReason.EXPIRED: DelegatedIdentityDecisionReason.ACCOUNT_EXPIRED,
        AccountDecisionReason.PURPOSE_NOT_ALLOWED: DelegatedIdentityDecisionReason.PURPOSE_MISMATCH,
        AccountDecisionReason.AUTHORIZATION_DOCUMENT_MISSING: (
            DelegatedIdentityDecisionReason.AUTHORIZATION_DOCUMENT_MISSING
        ),
    }
    return mapping[reason]


def _validate_scopes(scopes: frozenset[str]) -> None:
    if len(scopes) > 64:
        raise ValueError("approved scopes cannot exceed 64 entries")
    for scope in scopes:
        _bounded_required(scope, "scope", 200)


def _optional_reference(value: str | None, field_name: str) -> None:
    if value is not None:
        _bounded_required(value, field_name, 500)


def _optional_time(value: datetime | None, field_name: str) -> datetime | None:
    if value is None:
        return None
    return require_aware_utc(value, field_name=field_name)


def _bounded_required(value: str, field_name: str, maximum: int) -> None:
    normalized = value.strip()
    if not normalized or len(normalized) > maximum or "\x00" in normalized:
        raise ValueError(f"{field_name} is invalid")

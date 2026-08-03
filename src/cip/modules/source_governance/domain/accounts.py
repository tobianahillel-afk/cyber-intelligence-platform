from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from cip.shared.kernel.time import require_aware_utc, utc_now


class SourceAccountStatus(StrEnum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    MFA_REQUIRED = "mfa_required"
    EXPIRED = "expired"
    LOCKED = "locked"
    REVOKED = "revoked"


class SourceAccountAuthMode(StrEnum):
    API_KEY = "api_key"
    OAUTH = "oauth"
    SERVICE_ACCOUNT = "service_account"
    INTERACTIVE_SESSION = "interactive_session"


class AccountDecisionReason(StrEnum):
    ALLOWED = "allowed"
    NOT_ACTIVE = "not_active"
    EXPIRED = "expired"
    PURPOSE_NOT_ALLOWED = "purpose_not_allowed"
    AUTHORIZATION_DOCUMENT_MISSING = "authorization_document_missing"


@dataclass(frozen=True, slots=True)
class AccountUseDecision:
    allowed: bool
    reason: AccountDecisionReason


_ALLOWED_TRANSITIONS: dict[SourceAccountStatus, frozenset[SourceAccountStatus]] = {
    SourceAccountStatus.PENDING_VERIFICATION: frozenset(
        {
            SourceAccountStatus.ACTIVE,
            SourceAccountStatus.LOCKED,
            SourceAccountStatus.REVOKED,
        }
    ),
    SourceAccountStatus.ACTIVE: frozenset(
        {
            SourceAccountStatus.MFA_REQUIRED,
            SourceAccountStatus.EXPIRED,
            SourceAccountStatus.LOCKED,
            SourceAccountStatus.REVOKED,
        }
    ),
    SourceAccountStatus.MFA_REQUIRED: frozenset(
        {
            SourceAccountStatus.ACTIVE,
            SourceAccountStatus.LOCKED,
            SourceAccountStatus.REVOKED,
        }
    ),
    SourceAccountStatus.EXPIRED: frozenset(
        {SourceAccountStatus.PENDING_VERIFICATION, SourceAccountStatus.REVOKED}
    ),
    SourceAccountStatus.LOCKED: frozenset(
        {SourceAccountStatus.PENDING_VERIFICATION, SourceAccountStatus.REVOKED}
    ),
    SourceAccountStatus.REVOKED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class SourceAccount:
    source_id: str
    external_reference: str
    auth_mode: SourceAccountAuthMode
    status: SourceAccountStatus
    authorization_document_reference: str | None
    approved_purposes: frozenset[str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    verified_at: datetime | None = None
    expires_at: datetime | None = None
    last_used_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.external_reference.strip():
            raise ValueError("source_id and external_reference are required")
        object.__setattr__(
            self,
            "created_at",
            require_aware_utc(self.created_at, field_name="created_at"),
        )
        for field_name in ("verified_at", "expires_at", "last_used_at"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    require_aware_utc(value, field_name=field_name),
                )
        if self.status is SourceAccountStatus.ACTIVE:
            if not self.authorization_document_reference:
                raise ValueError("active account requires an authorization document")
            if self.verified_at is None:
                raise ValueError("active account requires verified_at")
        if self.expires_at is not None and self.expires_at <= self.created_at:
            raise ValueError("expires_at must be later than created_at")

    def evaluate_use(self, purpose: str, *, now: datetime) -> AccountUseDecision:
        current = require_aware_utc(now, field_name="now")
        if self.status is not SourceAccountStatus.ACTIVE:
            return AccountUseDecision(False, AccountDecisionReason.NOT_ACTIVE)
        if self.expires_at is not None and self.expires_at <= current:
            return AccountUseDecision(False, AccountDecisionReason.EXPIRED)
        if not self.authorization_document_reference:
            return AccountUseDecision(
                False,
                AccountDecisionReason.AUTHORIZATION_DOCUMENT_MISSING,
            )
        if purpose not in self.approved_purposes:
            return AccountUseDecision(False, AccountDecisionReason.PURPOSE_NOT_ALLOWED)
        return AccountUseDecision(True, AccountDecisionReason.ALLOWED)

    def transition(
        self,
        new_status: SourceAccountStatus,
        *,
        at: datetime,
        verified: bool = False,
    ) -> SourceAccount:
        transition_at = require_aware_utc(at, field_name="at")
        if new_status not in _ALLOWED_TRANSITIONS[self.status]:
            raise ValueError(f"invalid account transition: {self.status} -> {new_status}")
        verified_at = transition_at if verified else self.verified_at
        return replace(self, status=new_status, verified_at=verified_at)

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from cip.modules.source_governance.domain.accounts import (
    SourceAccountAuthMode,
    SourceAccountStatus,
)
from cip.modules.source_governance.domain.delegated_browser_identity import DelegatedOwnerKind


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

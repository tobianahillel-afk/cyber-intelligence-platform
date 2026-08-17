from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from hmac import compare_digest
from uuid import UUID, uuid4

from cip.shared.kernel.time import require_aware_utc


class HumanCheckpointKind(StrEnum):
    MFA = "mfa"
    CAPTCHA = "captcha"
    OAUTH_CONSENT = "oauth_consent"
    SSO = "sso"
    IDENTITY_VERIFICATION = "identity_verification"
    PROVIDER_CHALLENGE = "provider_challenge"


class HumanCheckpointState(StrEnum):
    WAITING = "waiting"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"


class HumanCheckpointEventType(StrEnum):
    CREATED = "created"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"


@dataclass(frozen=True, slots=True)
class HumanCheckpointBinding:
    job_id: UUID
    source_id: str
    adapter_id: str
    delegated_identity_id: UUID
    purpose: str

    def __post_init__(self) -> None:
        for field_name in ("source_id", "adapter_id", "purpose"):
            value = getattr(self, field_name).strip()
            if not value or len(value) > 200:
                raise ValueError(f"{field_name} must be 1..200 characters")
            object.__setattr__(self, field_name, value)


@dataclass(frozen=True, slots=True)
class HumanCheckpointRequest:
    binding: HumanCheckpointBinding
    kind: HumanCheckpointKind
    correlation_digest: str
    session_reference: str | None
    created_at: datetime
    expires_at: datetime
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        created = require_aware_utc(self.created_at, field_name="created_at")
        expires = require_aware_utc(self.expires_at, field_name="expires_at")
        if expires <= created:
            raise ValueError("expires_at must be after created_at")
        if len(self.correlation_digest) != 64:
            raise ValueError("correlation_digest must be a SHA-256 hex digest")
        try:
            bytes.fromhex(self.correlation_digest)
        except ValueError as exc:
            raise ValueError("correlation_digest must be a SHA-256 hex digest") from exc
        if self.session_reference is not None:
            reference = self.session_reference.strip()
            if not reference or len(reference) > 500 or "://" not in reference:
                raise ValueError("session_reference must be a bounded reference URI")
            object.__setattr__(self, "session_reference", reference)
        object.__setattr__(self, "created_at", created)
        object.__setattr__(self, "expires_at", expires)

    @classmethod
    def from_correlation_token(
        cls,
        *,
        binding: HumanCheckpointBinding,
        kind: HumanCheckpointKind,
        correlation_token: str,
        session_reference: str | None,
        created_at: datetime,
        expires_at: datetime,
    ) -> HumanCheckpointRequest:
        return cls(
            binding=binding,
            kind=kind,
            correlation_digest=correlation_digest(correlation_token),
            session_reference=session_reference,
            created_at=created_at,
            expires_at=expires_at,
        )


@dataclass(frozen=True, slots=True)
class HumanCheckpointResumeRequest:
    checkpoint_id: UUID
    binding: HumanCheckpointBinding
    correlation_token: str
    actor_reference: str
    resumed_at: datetime

    def __post_init__(self) -> None:
        _validate_actor(self.actor_reference)
        correlation_digest(self.correlation_token)
        object.__setattr__(
            self,
            "resumed_at",
            require_aware_utc(self.resumed_at, field_name="resumed_at"),
        )


def correlation_digest(token: str) -> str:
    if len(token) < 16 or len(token) > 512 or token != token.strip():
        raise ValueError("correlation token must be 16..512 non-padded characters")
    return sha256(token.encode("utf-8")).hexdigest()


def correlation_matches(token: str, expected_digest: str) -> bool:
    return compare_digest(correlation_digest(token), expected_digest)


def validate_actor_reference(value: str) -> str:
    return _validate_actor(value)


def _validate_actor(value: str) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > 200:
        raise ValueError("actor_reference must be 1..200 characters")
    return normalized

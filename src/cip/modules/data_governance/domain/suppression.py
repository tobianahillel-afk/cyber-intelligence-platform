from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from hashlib import sha256
from hmac import compare_digest, new

from cip.shared.kernel.time import require_aware_utc


class SuppressionChannel(StrEnum):
    EMAIL = "email"
    PHONE = "phone"
    PROFESSIONAL_PROFILE = "professional_profile"
    ORGANIZATION = "organization"


class SuppressionReason(StrEnum):
    OBJECTION = "objection"
    UNSUBSCRIBED = "unsubscribed"
    LEGAL_RESTRICTION = "legal_restriction"
    DATA_QUALITY = "data_quality"
    INTERNAL_BLOCK = "internal_block"


@dataclass(frozen=True, slots=True)
class SuppressionEntry:
    subject_hash: str
    channel: SuppressionChannel
    reason: SuppressionReason
    created_at: datetime
    expires_at: datetime
    source: str

    def __post_init__(self) -> None:
        if len(self.subject_hash) != 64:
            raise ValueError("subject_hash must be a SHA-256 digest")
        if not self.source.strip():
            raise ValueError("suppression source is required")
        created_at = require_aware_utc(self.created_at, field_name="created_at")
        expires_at = require_aware_utc(self.expires_at, field_name="expires_at")
        if expires_at <= created_at:
            raise ValueError("expires_at must be later than created_at")
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "expires_at", expires_at)

    def matches(self, identifier: str, *, pepper: bytes) -> bool:
        candidate = hash_identifier(identifier, self.channel, pepper=pepper)
        return compare_digest(self.subject_hash, candidate)


def create_suppression(
    identifier: str,
    channel: SuppressionChannel,
    reason: SuppressionReason,
    *,
    pepper: bytes,
    now: datetime,
    minimum_retention_days: int,
    source: str,
) -> SuppressionEntry:
    if minimum_retention_days < 1:
        raise ValueError("minimum_retention_days must be positive")
    created_at = require_aware_utc(now, field_name="now")
    return SuppressionEntry(
        subject_hash=hash_identifier(identifier, channel, pepper=pepper),
        channel=channel,
        reason=reason,
        created_at=created_at,
        expires_at=created_at + timedelta(days=minimum_retention_days),
        source=source,
    )


def hash_identifier(
    identifier: str,
    channel: SuppressionChannel,
    *,
    pepper: bytes,
) -> str:
    normalized = normalize_identifier(identifier, channel)
    if not pepper:
        raise ValueError("suppression pepper is required")
    message = f"{channel.value}:{normalized}".encode()
    return new(pepper, message, sha256).hexdigest()


def normalize_identifier(identifier: str, channel: SuppressionChannel) -> str:
    normalized = identifier.strip()
    if not normalized:
        raise ValueError("identifier is required")
    if channel is SuppressionChannel.PHONE:
        normalized = "".join(character for character in normalized if character.isdigit())
        if not normalized:
            raise ValueError("phone identifier must contain digits")
        return normalized
    return normalized.casefold()

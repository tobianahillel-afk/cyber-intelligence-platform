from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from cip.shared.kernel.time import require_aware_utc


class NeedHypothesisClass(StrEnum):
    EXPLICIT_PROCUREMENT = "explicit_procurement"
    CONTRACT_RENEWAL_OR_REPLACEMENT = "contract_renewal_or_replacement"
    PROGRAM_BUILD_OR_TRANSFORMATION = "program_build_or_transformation"
    CAPABILITY_GAP = "capability_gap"
    INCIDENT_URGENCY = "incident_urgency"
    REGULATORY_DEADLINE_OR_GAP = "regulatory_deadline_or_gap"
    TECHNOLOGY_RISK_OR_LIFECYCLE = "technology_risk_or_lifecycle"
    EXTERNAL_EXPOSURE = "external_exposure"
    ORGANIZATIONAL_CHANGE = "organizational_change"
    PROVIDER_DISSATISFACTION_OR_TRANSITION = "provider_dissatisfaction_or_transition"
    SKILLS_AND_TRAINING_NEED = "skills_and_training_need"
    RESEARCH_ONLY_WEAK_SIGNAL = "research_only_weak_signal"


class EvidencePosition(StrEnum):
    SUPPORTING = "supporting"
    CONFLICTING = "conflicting"
    NEGATIVE = "negative"


class NeedUrgency(StrEnum):
    IMMEDIATE = "immediate"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    RESEARCH = "research"


class NeedHorizon(StrEnum):
    NOW = "now"
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class EvidenceContribution:
    evidence_id: UUID
    source_id: str
    corroboration_group_key: str
    position: EvidencePosition
    confidence: float
    effective_at: datetime
    signal_id: UUID | None = None
    expires_at: datetime | None = None
    source_record_key: str | None = None
    content_hash_sha256: str | None = None

    def __post_init__(self) -> None:
        source_id = _required_text(self.source_id, "source_id", maximum=100)
        group_key = _required_text(
            self.corroboration_group_key,
            "corroboration_group_key",
            maximum=300,
        )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        effective_at = require_aware_utc(self.effective_at, field_name="effective_at")
        expires_at = self.expires_at
        if expires_at is not None:
            expires_at = require_aware_utc(expires_at, field_name="expires_at")
            if expires_at <= effective_at:
                raise ValueError("expires_at must be later than effective_at")
        record_key = _optional_text(self.source_record_key, maximum=500)
        content_hash = _optional_hash(self.content_hash_sha256)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "corroboration_group_key", group_key)
        object.__setattr__(self, "effective_at", effective_at)
        object.__setattr__(self, "expires_at", expires_at)
        object.__setattr__(self, "source_record_key", record_key)
        object.__setattr__(self, "content_hash_sha256", content_hash)

    @property
    def independence_key(self) -> str:
        return self.corroboration_group_key

    def is_current_at(self, now: datetime) -> bool:
        current = require_aware_utc(now, field_name="now")
        return self.expires_at is None or self.expires_at > current


def _required_text(value: str, field_name: str, *, maximum: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > maximum:
        raise ValueError(f"{field_name} cannot exceed {maximum} characters")
    return normalized


def _optional_text(value: str | None, *, maximum: int) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > maximum:
        raise ValueError(f"value cannot exceed {maximum} characters")
    return normalized


def _optional_hash(value: str | None) -> str | None:
    normalized = _optional_text(value, maximum=64)
    if normalized is None:
        return None
    invalid_character = any(
        character not in "0123456789abcdef" for character in normalized
    )
    if len(normalized) != 64 or invalid_character:
        raise ValueError("content_hash_sha256 must be a lowercase SHA-256 digest")
    return normalized

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from cip.shared.kernel.time import require_aware_utc, utc_now


class ClaimType(StrEnum):
    ACTOR_CLAIM = "actor_claim"
    MEDIA_REPORT = "media_report"
    OFFICIAL_STATEMENT = "official_statement"
    AUTHORITY_NOTICE = "authority_notice"
    ANALYST_INFERENCE = "analyst_inference"
    CORRECTION = "correction"
    DENIAL = "denial"


class VerificationStatus(StrEnum):
    UNVERIFIED = "unverified"
    PARTIALLY_CORROBORATED = "partially_corroborated"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    RETRACTED = "retracted"


class CyberEventType(StrEnum):
    RANSOMWARE_CLAIM = "ransomware_claim"
    CONFIRMED_RANSOMWARE_INCIDENT = "confirmed_ransomware_incident"
    DATA_BREACH = "data_breach"
    SERVICE_DISRUPTION = "service_disruption"
    VULNERABILITY_EXPOSURE_SIGNAL = "vulnerability_exposure_signal"
    REGULATORY_NOTICE = "regulatory_notice"
    PUBLIC_SECURITY_STATEMENT = "public_security_statement"


@dataclass(frozen=True, slots=True)
class CyberEvent:
    event_type: CyberEventType
    canonical_title: str
    first_seen_at: datetime
    id: UUID = field(default_factory=uuid4)
    organization_id: UUID | None = None
    occurred_at: datetime | None = None
    last_updated_at: datetime = field(default_factory=utc_now)
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if not self.canonical_title.strip():
            raise ValueError("canonical_title is required")
        if len(self.canonical_title) > 500:
            raise ValueError("canonical_title cannot exceed 500 characters")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(
            self,
            "first_seen_at",
            require_aware_utc(self.first_seen_at, field_name="first_seen_at"),
        )
        object.__setattr__(
            self,
            "last_updated_at",
            require_aware_utc(self.last_updated_at, field_name="last_updated_at"),
        )
        if self.occurred_at is not None:
            object.__setattr__(
                self,
                "occurred_at",
                require_aware_utc(self.occurred_at, field_name="occurred_at"),
            )
        if self.last_updated_at < self.first_seen_at:
            raise ValueError("last_updated_at cannot precede first_seen_at")


@dataclass(frozen=True, slots=True)
class EventClaim:
    event_id: UUID
    claim_type: ClaimType
    claimant_name: str
    statement_summary: str
    evidence_id: UUID
    id: UUID = field(default_factory=uuid4)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    observed_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.claimant_name.strip():
            raise ValueError("claimant_name is required")
        if not self.statement_summary.strip():
            raise ValueError("statement_summary is required")
        if len(self.statement_summary) > 4_000:
            raise ValueError("statement_summary cannot exceed 4000 characters")
        object.__setattr__(
            self,
            "observed_at",
            require_aware_utc(self.observed_at, field_name="observed_at"),
        )

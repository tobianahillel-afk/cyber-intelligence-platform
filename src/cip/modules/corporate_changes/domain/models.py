from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlparse
from uuid import UUID

from cip.shared.kernel.time import require_aware_utc

MAX_EXCERPT_LENGTH = 500


class ChangeEventType(StrEnum):
    ACQUISITION = "acquisition"
    LEADERSHIP = "leadership"
    FUNDING = "funding"
    RESTRUCTURING = "restructuring"
    GEOGRAPHIC_EXPANSION = "geographic_expansion"
    CLOUD_DIGITAL_PROGRAM = "cloud_digital_program"
    REGULATORY_ACTION = "regulatory_action"
    BREACH = "breach"
    AUDIT = "audit"
    CERTIFICATION = "certification"
    SECURITY_COMMITMENT = "security_commitment"
    OTHER = "other"


class ChangeClaimType(StrEnum):
    CONFIRMATION = "confirmation"
    REPORT = "report"
    SPECULATION = "speculation"
    DISPUTE = "dispute"
    CORRECTION = "correction"
    RETRACTION = "retraction"


class ChangeEventStatus(StrEnum):
    UNDER_REVIEW = "under_review"
    SPECULATIVE = "speculative"
    REPORTED = "reported"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    CORRECTED = "corrected"
    RETRACTED = "retracted"
    STALE = "stale"


class ChangeSourceKind(StrEnum):
    OFFICIAL_FILING = "official_filing"
    REGULATOR = "regulator"
    COMPANY = "company"
    MEDIA = "media"
    ANALYST = "analyst"
    OTHER = "other"


class OrganizationLinkStatus(StrEnum):
    UNRESOLVED = "unresolved"
    EXACT = "exact"
    CANDIDATE = "candidate"
    REVIEW_REQUIRED = "review_required"
    REJECTED = "rejected"


_OFFICIAL_SOURCE_KINDS = {
    ChangeSourceKind.OFFICIAL_FILING,
    ChangeSourceKind.REGULATOR,
    ChangeSourceKind.COMPANY,
}


@dataclass(frozen=True, slots=True)
class ChangeClaimSnapshot:
    source_id: str
    source_kind: ChangeSourceKind
    source_record_key: str
    article_id: str
    source_url: str
    event_key: str
    claim_type: ChangeClaimType
    event_type: ChangeEventType
    title: str
    excerpt: str
    claimed_organization_name: str | None
    organization_id: UUID | None
    organization_link_status: OrganizationLinkStatus
    published_at: datetime
    modified_at: datetime
    event_at: datetime | None = None
    expires_at: datetime | None = None
    independence_key: str | None = None
    syndication_group_key: str | None = None
    confidence: float = 0.5
    active: bool = True
    historical_only: bool = False
    metadata_only: bool = True
    supersedes_record_key: str | None = None

    def __post_init__(self) -> None:
        _validate_identifier(self.source_id, "source_id", maximum=200)
        _validate_identifier(self.source_record_key, "source_record_key", maximum=500)
        _validate_identifier(self.article_id, "article_id", maximum=500)
        _validate_identifier(self.event_key, "event_key", maximum=500)
        _validate_text(self.title, "title", maximum=1_000)
        _validate_text(self.excerpt, "excerpt", maximum=MAX_EXCERPT_LENGTH)
        _validate_optional_text(
            self.claimed_organization_name,
            "claimed_organization_name",
            maximum=500,
        )
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if not self.metadata_only:
            raise ValueError("corporate change intelligence accepts metadata only")
        _validate_organization_link(self)
        parsed = urlparse(self.source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source_url must use http or https")
        _normalize_timestamps(self)
        if self.modified_at < self.published_at:
            raise ValueError("modified_at cannot precede published_at")
        if self.expires_at is not None and self.expires_at < self.published_at:
            raise ValueError("expires_at cannot precede published_at")
        _normalize_keys(self)

    @property
    def is_official_confirmation(self) -> bool:
        return (
            self.active
            and self.claim_type is ChangeClaimType.CONFIRMATION
            and self.source_kind in _OFFICIAL_SOURCE_KINDS
        )

    @property
    def corroboration_key(self) -> str:
        return self.syndication_group_key or self.independence_key or self.source_id

    def is_stale_at(self, now: datetime) -> bool:
        current = require_aware_utc(now, field_name="now")
        return self.expires_at is not None and self.expires_at <= current


@dataclass(frozen=True, slots=True)
class ReconciledChangeEvent:
    event_key: str
    event_type: ChangeEventType
    title: str
    excerpt: str
    status: ChangeEventStatus
    organization_id: UUID | None
    organization_link_status: OrganizationLinkStatus
    claimed_organization_names: tuple[str, ...]
    event_at: datetime | None
    first_published_at: datetime
    last_updated_at: datetime
    claim_count: int
    independent_source_count: int
    officially_confirmed: bool
    has_dispute: bool
    has_correction: bool
    has_retraction: bool
    historical_only: bool


@dataclass(frozen=True, slots=True)
class ChangeServiceMapping:
    event_key: str
    service_family: str
    rationale: str
    confidence: float

    def __post_init__(self) -> None:
        _validate_identifier(self.event_key, "event_key", maximum=500)
        _validate_identifier(self.service_family, "service_family", maximum=120)
        _validate_text(self.rationale, "rationale", maximum=1_000)
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")


def _validate_organization_link(snapshot: ChangeClaimSnapshot) -> None:
    if (
        snapshot.organization_link_status is OrganizationLinkStatus.EXACT
        and snapshot.organization_id is None
    ):
        raise ValueError("exact organization links require organization_id")
    if (
        snapshot.organization_id is not None
        and snapshot.organization_link_status
        in {OrganizationLinkStatus.UNRESOLVED, OrganizationLinkStatus.REJECTED}
    ):
        raise ValueError("unresolved or rejected organization links cannot retain organization_id")


def _normalize_timestamps(snapshot: ChangeClaimSnapshot) -> None:
    for field_name in ("published_at", "modified_at", "event_at", "expires_at"):
        value = getattr(snapshot, field_name)
        if value is not None:
            object.__setattr__(
                snapshot,
                field_name,
                require_aware_utc(value, field_name=field_name),
            )


def _normalize_keys(snapshot: ChangeClaimSnapshot) -> None:
    if snapshot.independence_key is None:
        object.__setattr__(snapshot, "independence_key", snapshot.source_id)
    else:
        _validate_identifier(snapshot.independence_key, "independence_key", maximum=500)
    if snapshot.syndication_group_key is not None:
        _validate_identifier(
            snapshot.syndication_group_key,
            "syndication_group_key",
            maximum=500,
        )
    if snapshot.supersedes_record_key is not None:
        _validate_identifier(
            snapshot.supersedes_record_key,
            "supersedes_record_key",
            maximum=500,
        )


def _validate_text(value: str, name: str, *, maximum: int) -> None:
    if not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must be between 1 and {maximum} characters")


def _validate_optional_text(value: str | None, name: str, *, maximum: int) -> None:
    if value is not None:
        _validate_text(value, name, maximum=maximum)


def _validate_identifier(value: str, name: str, *, maximum: int) -> None:
    _validate_text(value, name, maximum=maximum)

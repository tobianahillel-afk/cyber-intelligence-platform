from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlparse
from uuid import UUID

from cip.shared.kernel.time import require_aware_utc


class IncidentType(StrEnum):
    RANSOMWARE = "ransomware"
    DATA_BREACH = "data_breach"
    EXTORTION = "extortion"
    BUSINESS_EMAIL_COMPROMISE = "business_email_compromise"
    SERVICE_DISRUPTION = "service_disruption"
    SUPPLY_CHAIN = "supply_chain"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    MALWARE = "malware"
    UNKNOWN = "unknown"


class IncidentClaimType(StrEnum):
    ATTACKER_ALLEGATION = "attacker_allegation"
    MEDIA_REPORT = "media_report"
    RESEARCHER_REPORT = "researcher_report"
    COMPANY_CONFIRMATION = "company_confirmation"
    REGULATOR_NOTICE = "regulator_notice"
    CERT_NOTICE = "cert_notice"
    PROVIDER_STATEMENT = "provider_statement"
    DENIAL = "denial"
    CORRECTION = "correction"
    RETRACTION = "retraction"


class IncidentStatus(StrEnum):
    UNDER_REVIEW = "under_review"
    ALLEGED = "alleged"
    REPORTED = "reported"
    CONFIRMED = "confirmed"
    DENIED = "denied"
    RETRACTED = "retracted"
    RESOLVED = "resolved"


class OrganizationLinkStatus(StrEnum):
    UNRESOLVED = "unresolved"
    EXACT = "exact"
    CANDIDATE = "candidate"
    REVIEW_REQUIRED = "review_required"
    REJECTED = "rejected"


class IncidentSourceKind(StrEnum):
    COMPANY = "company"
    REGULATOR = "regulator"
    CERT = "cert"
    MEDIA = "media"
    RESEARCH = "research"
    PROVIDER = "provider"
    RANSOMWARE_METADATA = "ransomware_metadata"
    OTHER = "other"


_OFFICIAL_CLAIM_TYPES = {
    IncidentClaimType.COMPANY_CONFIRMATION,
    IncidentClaimType.REGULATOR_NOTICE,
    IncidentClaimType.CERT_NOTICE,
}


@dataclass(frozen=True, slots=True)
class IncidentClaimSnapshot:
    source_id: str
    source_kind: IncidentSourceKind
    source_record_key: str
    source_url: str
    incident_key: str
    claim_type: IncidentClaimType
    incident_type: IncidentType
    title: str
    summary: str
    claimed_organization_name: str | None
    organization_id: UUID | None
    organization_link_status: OrganizationLinkStatus
    published_at: datetime
    modified_at: datetime
    occurrence_start_at: datetime | None = None
    occurrence_end_at: datetime | None = None
    discovered_at: datetime | None = None
    confirmed_at: datetime | None = None
    independence_key: str | None = None
    confidence: float = 0.5
    active: bool = True
    historical_only: bool = False
    metadata_only: bool = True
    supersedes_record_key: str | None = None

    def __post_init__(self) -> None:
        _validate_identifier(self.source_id, "source_id", maximum=200)
        _validate_identifier(
            self.source_record_key,
            "source_record_key",
            maximum=500,
        )
        _validate_identifier(self.incident_key, "incident_key", maximum=500)
        if not self.title.strip() or len(self.title) > 1_000:
            raise ValueError("title must be between 1 and 1000 characters")
        if not self.summary.strip() or len(self.summary) > 8_000:
            raise ValueError("summary must be between 1 and 8000 characters")
        if (
            self.claimed_organization_name is not None
            and (
                not self.claimed_organization_name.strip()
                or len(self.claimed_organization_name) > 500
            )
        ):
            raise ValueError(
                "claimed_organization_name must be a non-empty bounded value"
            )
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if not self.metadata_only:
            raise ValueError("incident intelligence accepts metadata only")
        if (
            self.organization_link_status is OrganizationLinkStatus.EXACT
            and self.organization_id is None
        ):
            raise ValueError("exact organization links require organization_id")
        if (
            self.organization_id is not None
            and self.organization_link_status
            in {
                OrganizationLinkStatus.UNRESOLVED,
                OrganizationLinkStatus.REJECTED,
            }
        ):
            raise ValueError(
                "unresolved or rejected organization links cannot retain organization_id"
            )
        parsed = urlparse(self.source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source_url must use http or https")
        _normalize_timestamps(self)
        if self.modified_at < self.published_at:
            raise ValueError("modified_at cannot precede published_at")
        if (
            self.occurrence_start_at is not None
            and self.occurrence_end_at is not None
            and self.occurrence_end_at < self.occurrence_start_at
        ):
            raise ValueError("occurrence_end_at cannot precede occurrence_start_at")
        if self.confirmed_at is not None and self.claim_type not in _OFFICIAL_CLAIM_TYPES:
            raise ValueError("confirmed_at is reserved for official confirmation claims")
        if self.independence_key is None:
            object.__setattr__(self, "independence_key", self.source_id)
        else:
            _validate_identifier(
                self.independence_key,
                "independence_key",
                maximum=500,
            )
        if self.supersedes_record_key is not None:
            _validate_identifier(
                self.supersedes_record_key,
                "supersedes_record_key",
                maximum=500,
            )

    @property
    def is_official_confirmation(self) -> bool:
        return self.claim_type in _OFFICIAL_CLAIM_TYPES and self.active

    @property
    def is_positive_claim(self) -> bool:
        return self.claim_type not in {
            IncidentClaimType.DENIAL,
            IncidentClaimType.CORRECTION,
            IncidentClaimType.RETRACTION,
        }


@dataclass(frozen=True, slots=True)
class ReconciledIncident:
    incident_key: str
    incident_type: IncidentType
    title: str
    summary: str
    status: IncidentStatus
    organization_id: UUID | None
    organization_link_status: OrganizationLinkStatus
    claimed_organization_names: tuple[str, ...]
    occurrence_start_at: datetime | None
    occurrence_end_at: datetime | None
    discovered_at: datetime | None
    first_published_at: datetime
    confirmed_at: datetime | None
    last_updated_at: datetime
    claim_count: int
    independent_source_count: int
    officially_confirmed: bool
    has_denial: bool
    has_retraction: bool
    historical_only: bool


def _normalize_timestamps(snapshot: IncidentClaimSnapshot) -> None:
    for field_name in (
        "published_at",
        "modified_at",
        "occurrence_start_at",
        "occurrence_end_at",
        "discovered_at",
        "confirmed_at",
    ):
        value = getattr(snapshot, field_name)
        if value is not None:
            object.__setattr__(
                snapshot,
                field_name,
                require_aware_utc(value, field_name=field_name),
            )


def _validate_identifier(value: str, name: str, *, maximum: int) -> None:
    if not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must be between 1 and {maximum} characters")

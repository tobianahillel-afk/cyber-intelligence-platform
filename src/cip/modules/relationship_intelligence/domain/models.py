from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlparse
from uuid import UUID

from cip.shared.kernel.time import require_aware_utc

MAX_RELATIONSHIP_EXCERPT_LENGTH = 500


class RelationshipRole(StrEnum):
    PROVIDER = "provider"
    CUSTOMER = "customer"
    PARTNER = "partner"
    SUPPLIER = "supplier"
    RESELLER = "reseller"
    DISTRIBUTOR = "distributor"
    INTEGRATOR = "integrator"
    AUDITOR = "auditor"
    INSURER = "insurer"
    MSSP_MDR = "mssp_mdr"
    CLOUD_HOSTING_PROVIDER = "cloud_hosting_provider"
    TECHNOLOGY_VENDOR = "technology_vendor"
    SUBCONTRACTOR = "subcontractor"
    OTHER = "other"


class RelationshipEvidenceClass(StrEnum):
    CLAIMED = "claimed"
    OBSERVED = "observed"
    CONTRACTED = "contracted"
    HISTORICAL = "historical"
    INFERRED = "inferred"


class RelationshipClaimType(StrEnum):
    ASSERTION = "assertion"
    DISPUTE = "dispute"
    CORRECTION = "correction"
    RETRACTION = "retraction"


class RelationshipStatus(StrEnum):
    UNDER_REVIEW = "under_review"
    CLAIMED = "claimed"
    INFERRED = "inferred"
    ACTIVE = "active"
    HISTORICAL = "historical"
    DISPUTED = "disputed"
    CORRECTED = "corrected"
    RETRACTED = "retracted"
    STALE = "stale"


class RelationshipSourceKind(StrEnum):
    PROCUREMENT = "procurement"
    OFFICIAL_DISCLOSURE = "official_disclosure"
    CASE_STUDY = "case_study"
    PARTNER_DIRECTORY = "partner_directory"
    CERTIFICATE = "certificate"
    PASSIVE_OBSERVATION = "passive_observation"
    REGULATORY_FILING = "regulatory_filing"
    LICENSED_METADATA = "licensed_metadata"
    OTHER = "other"


class RelationshipOrganizationLinkStatus(StrEnum):
    UNRESOLVED = "unresolved"
    EXACT = "exact"
    CANDIDATE = "candidate"
    REVIEW_REQUIRED = "review_required"
    REJECTED = "rejected"


_ACTIVE_EVIDENCE_CLASSES = {
    RelationshipEvidenceClass.OBSERVED,
    RelationshipEvidenceClass.CONTRACTED,
}
_INCUMBENT_ROLES = {
    RelationshipRole.PROVIDER,
    RelationshipRole.SUPPLIER,
    RelationshipRole.INTEGRATOR,
    RelationshipRole.AUDITOR,
    RelationshipRole.INSURER,
    RelationshipRole.MSSP_MDR,
    RelationshipRole.CLOUD_HOSTING_PROVIDER,
    RelationshipRole.TECHNOLOGY_VENDOR,
    RelationshipRole.SUBCONTRACTOR,
}


@dataclass(frozen=True, slots=True)
class RelationshipEvidenceSnapshot:
    source_id: str
    source_kind: RelationshipSourceKind
    source_record_key: str
    source_url: str
    relationship_key: str
    claim_type: RelationshipClaimType
    role: RelationshipRole
    evidence_class: RelationshipEvidenceClass
    title: str
    excerpt: str
    claimed_source_organization_name: str | None
    claimed_target_organization_name: str | None
    source_organization_id: UUID | None
    target_organization_id: UUID | None
    source_link_status: RelationshipOrganizationLinkStatus
    target_link_status: RelationshipOrganizationLinkStatus
    published_at: datetime
    modified_at: datetime
    observed_at: datetime
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    expires_at: datetime | None = None
    contract_reference: str | None = None
    product_context: str | None = None
    service_context: str | None = None
    renewal_at: datetime | None = None
    independence_key: str | None = None
    confidence: float = 0.5
    active: bool = True
    historical_only: bool = False
    metadata_only: bool = True
    supersedes_record_key: str | None = None

    def __post_init__(self) -> None:
        _validate_identifier(self.source_id, "source_id", maximum=200)
        _validate_identifier(self.source_record_key, "source_record_key", maximum=500)
        _validate_identifier(self.relationship_key, "relationship_key", maximum=500)
        _validate_text(self.title, "title", maximum=1_000)
        _validate_text(self.excerpt, "excerpt", maximum=MAX_RELATIONSHIP_EXCERPT_LENGTH)
        _validate_optional_text(
            self.claimed_source_organization_name,
            "claimed_source_organization_name",
            maximum=500,
        )
        _validate_optional_text(
            self.claimed_target_organization_name,
            "claimed_target_organization_name",
            maximum=500,
        )
        _validate_optional_text(self.contract_reference, "contract_reference", maximum=500)
        _validate_optional_text(self.product_context, "product_context", maximum=500)
        _validate_optional_text(self.service_context, "service_context", maximum=500)
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if not self.metadata_only:
            raise ValueError("relationship intelligence accepts metadata only")
        _validate_link(self.source_organization_id, self.source_link_status, "source")
        _validate_link(self.target_organization_id, self.target_link_status, "target")
        if (
            self.source_organization_id is not None
            and self.source_organization_id == self.target_organization_id
        ):
            raise ValueError("relationship source and target organizations must differ")
        parsed = urlparse(self.source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source_url must use http or https")
        _normalize_timestamps(self)
        _validate_chronology(self)
        _validate_contract_context(self)
        _normalize_keys(self)
        if self.evidence_class is RelationshipEvidenceClass.HISTORICAL:
            object.__setattr__(self, "historical_only", True)

    @property
    def is_positive_assertion(self) -> bool:
        return self.active and self.claim_type is RelationshipClaimType.ASSERTION

    def is_stale_at(self, now: datetime) -> bool:
        current = require_aware_utc(now, field_name="now")
        return self.expires_at is not None and self.expires_at <= current

    def is_historical_at(self, now: datetime) -> bool:
        current = require_aware_utc(now, field_name="now")
        return (
            self.historical_only
            or self.evidence_class is RelationshipEvidenceClass.HISTORICAL
            or (self.valid_until is not None and self.valid_until <= current)
        )

    def is_current_at(self, now: datetime) -> bool:
        current = require_aware_utc(now, field_name="now")
        if not self.is_positive_assertion or self.is_stale_at(current):
            return False
        if self.is_historical_at(current):
            return False
        return self.valid_from is None or self.valid_from <= current

    def supports_active_relationship_at(self, now: datetime) -> bool:
        return self.evidence_class in _ACTIVE_EVIDENCE_CLASSES and self.is_current_at(now)

    def is_contract_evidence_at(self, now: datetime) -> bool:
        return (
            self.evidence_class is RelationshipEvidenceClass.CONTRACTED
            and self.is_current_at(now)
        )


@dataclass(frozen=True, slots=True)
class ReconciledRelationship:
    relationship_key: str
    role: RelationshipRole
    status: RelationshipStatus
    source_organization_id: UUID | None
    target_organization_id: UUID | None
    source_link_status: RelationshipOrganizationLinkStatus
    target_link_status: RelationshipOrganizationLinkStatus
    claimed_source_organization_names: tuple[str, ...]
    claimed_target_organization_names: tuple[str, ...]
    valid_from: datetime | None
    valid_until: datetime | None
    first_published_at: datetime
    last_updated_at: datetime
    last_observed_at: datetime
    evidence_count: int
    independent_source_count: int
    strongest_evidence_class: RelationshipEvidenceClass
    confidence: float
    has_contract_evidence: bool
    contract_backed_current: bool
    next_renewal_at: datetime | None
    has_role_conflict: bool
    has_dispute: bool
    has_correction: bool
    has_retraction: bool
    historical_only: bool


@dataclass(frozen=True, slots=True)
class RelationshipContext:
    relationship_key: str
    context_type: str
    value: str
    reference: str | None = None
    confidence: float = 0.5

    def __post_init__(self) -> None:
        _validate_identifier(self.relationship_key, "relationship_key", maximum=500)
        if self.context_type not in {"product", "service", "contract"}:
            raise ValueError("context_type must be product, service, or contract")
        _validate_text(self.value, "value", maximum=500)
        _validate_optional_text(self.reference, "reference", maximum=500)
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")


def role_can_be_contract_backed_incumbent(role: RelationshipRole) -> bool:
    return role in _INCUMBENT_ROLES


def _validate_link(
    organization_id: UUID | None,
    status: RelationshipOrganizationLinkStatus,
    side: str,
) -> None:
    if status is RelationshipOrganizationLinkStatus.EXACT and organization_id is None:
        raise ValueError(f"exact {side} organization links require organization_id")
    if organization_id is not None and status in {
        RelationshipOrganizationLinkStatus.UNRESOLVED,
        RelationshipOrganizationLinkStatus.REJECTED,
    }:
        raise ValueError(f"unresolved or rejected {side} links cannot retain organization_id")


def _normalize_timestamps(snapshot: RelationshipEvidenceSnapshot) -> None:
    fields = (
        "published_at",
        "modified_at",
        "observed_at",
        "valid_from",
        "valid_until",
        "expires_at",
        "renewal_at",
    )
    for field_name in fields:
        value = getattr(snapshot, field_name)
        if value is not None:
            object.__setattr__(
                snapshot,
                field_name,
                require_aware_utc(value, field_name=field_name),
            )


def _validate_chronology(snapshot: RelationshipEvidenceSnapshot) -> None:
    if snapshot.modified_at < snapshot.published_at:
        raise ValueError("modified_at cannot precede published_at")
    if (
        snapshot.valid_from is not None
        and snapshot.valid_until is not None
        and snapshot.valid_until < snapshot.valid_from
    ):
        raise ValueError("valid_until cannot precede valid_from")
    if snapshot.expires_at is not None and snapshot.expires_at < snapshot.published_at:
        raise ValueError("expires_at cannot precede published_at")


def _validate_contract_context(snapshot: RelationshipEvidenceSnapshot) -> None:
    has_contract_context = (
        snapshot.contract_reference is not None or snapshot.renewal_at is not None
    )
    if (
        has_contract_context
        and snapshot.evidence_class is not RelationshipEvidenceClass.CONTRACTED
    ):
        raise ValueError("contract reference and renewal require contracted evidence")


def _normalize_keys(snapshot: RelationshipEvidenceSnapshot) -> None:
    if snapshot.independence_key is None:
        object.__setattr__(snapshot, "independence_key", snapshot.source_id)
    else:
        _validate_identifier(snapshot.independence_key, "independence_key", maximum=500)
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

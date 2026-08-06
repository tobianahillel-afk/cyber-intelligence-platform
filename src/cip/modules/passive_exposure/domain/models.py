from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlsplit
from uuid import UUID

from cip.modules.passive_exposure.domain.normalization import (
    normalize_asn,
    normalize_certificate_fingerprint,
    normalize_cloud_resource,
    normalize_domain,
    normalize_hostname,
    normalize_ip,
    normalize_optional_text,
    normalize_port,
    normalize_protocol,
)
from cip.shared.kernel.time import require_aware_utc


class PassiveAssetKind(StrEnum):
    DOMAIN = "domain"
    HOSTNAME = "hostname"
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    CERTIFICATE = "certificate"
    ASN = "asn"
    CLOUD_RESOURCE = "cloud_resource"


class PassiveObservationKind(StrEnum):
    PASSIVE_DNS = "passive_dns"
    CERTIFICATE = "certificate"
    ASN = "asn"
    CLOUD = "cloud"
    SERVICE = "service"
    PORT = "port"
    PRODUCT = "product"
    VERSION = "version"
    TECHNOLOGY_MENTION = "technology_mention"


class PassiveObservationState(StrEnum):
    CURRENT = "current"
    HISTORICAL = "historical"
    EXPIRED = "expired"
    CORRECTED = "corrected"
    RETRACTED = "retracted"
    DELETED = "deleted"
    UNKNOWN = "unknown"


class OrganizationLinkStatus(StrEnum):
    UNRESOLVED = "unresolved"
    EXACT = "exact"
    CANDIDATE = "candidate"
    REVIEW_REQUIRED = "review_required"
    REJECTED = "rejected"


class OrganizationLinkMethod(StrEnum):
    EXACT_OFFICIAL_DOMAIN = "exact_official_domain"
    EXACT_OFFICIAL_IDENTIFIER = "exact_official_identifier"
    PROVIDER_ASSERTION = "provider_assertion"
    PASSIVE_CORRELATION = "passive_correlation"
    NAME_ONLY = "name_only"
    NONE = "none"


class AttributionRisk(StrEnum):
    SHARED_HOSTING = "shared_hosting"
    CDN = "cdn"
    RESELLER = "reseller"
    SUBSIDIARY = "subsidiary"
    ABANDONED_DOMAIN = "abandoned_domain"
    REASSIGNED_ADDRESS = "reassigned_address"


class TechnologyEvidenceLevel(StrEnum):
    TECHNOLOGY_MENTION = "technology_mention"
    PASSIVE_OBSERVATION = "passive_observation"
    OBSERVED_VERSION = "observed_version"


_EXACT_LINK_METHODS = {
    OrganizationLinkMethod.EXACT_OFFICIAL_DOMAIN,
    OrganizationLinkMethod.EXACT_OFFICIAL_IDENTIFIER,
}
_TERMINAL_STATES = {
    PassiveObservationState.EXPIRED,
    PassiveObservationState.RETRACTED,
    PassiveObservationState.DELETED,
}


@dataclass(frozen=True, slots=True)
class PassiveAsset:
    kind: PassiveAssetKind
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", normalize_asset(self.kind, self.value))

    @property
    def key(self) -> str:
        return f"{self.kind.value}:{self.value}"


@dataclass(frozen=True, slots=True)
class OrganizationLink:
    status: OrganizationLinkStatus
    method: OrganizationLinkMethod
    confidence: float
    organization_id: UUID | None = None
    reasons: tuple[str, ...] = ()
    attribution_risks: tuple[AttributionRisk, ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("organization-link confidence must be between 0 and 1")
        reasons = _unique_text(self.reasons, maximum=500)
        risks = tuple(dict.fromkeys(self.attribution_risks))
        object.__setattr__(self, "reasons", reasons)
        object.__setattr__(self, "attribution_risks", risks)
        if self.status in {
            OrganizationLinkStatus.UNRESOLVED,
            OrganizationLinkStatus.REJECTED,
        } and self.organization_id is not None:
            raise ValueError("unresolved or rejected links cannot retain organization_id")
        if self.status in {
            OrganizationLinkStatus.EXACT,
            OrganizationLinkStatus.CANDIDATE,
            OrganizationLinkStatus.REVIEW_REQUIRED,
        } and self.organization_id is None:
            raise ValueError("resolved or reviewable links require organization_id")
        if self.status is OrganizationLinkStatus.EXACT:
            if self.method not in _EXACT_LINK_METHODS:
                raise ValueError("exact links require exact official evidence")
            if risks:
                raise ValueError("attribution risks prevent an exact organization link")
        if self.method is OrganizationLinkMethod.NAME_ONLY and self.status not in {
            OrganizationLinkStatus.REVIEW_REQUIRED,
            OrganizationLinkStatus.REJECTED,
        }:
            raise ValueError("name-only links must remain reviewable or rejected")
        if self.status is not OrganizationLinkStatus.UNRESOLVED and not reasons:
            raise ValueError("linked records require at least one explicit reason")
        if self.status is OrganizationLinkStatus.UNRESOLVED:
            if self.method is not OrganizationLinkMethod.NONE:
                raise ValueError("unresolved links must use method none")
            if reasons:
                raise ValueError("unresolved links cannot retain link reasons")

    @property
    def requires_review(self) -> bool:
        return self.status in {
            OrganizationLinkStatus.CANDIDATE,
            OrganizationLinkStatus.REVIEW_REQUIRED,
        }


@dataclass(frozen=True, slots=True)
class TechnologyObservation:
    evidence_level: TechnologyEvidenceLevel
    product_name: str | None = None
    product_version: str | None = None
    component_name: str | None = None

    def __post_init__(self) -> None:
        product_name = normalize_optional_text(self.product_name, maximum=300)
        product_version = normalize_optional_text(self.product_version, maximum=200)
        component_name = normalize_optional_text(self.component_name, maximum=300)
        object.__setattr__(self, "product_name", product_name)
        object.__setattr__(self, "product_version", product_version)
        object.__setattr__(self, "component_name", component_name)
        if self.evidence_level is TechnologyEvidenceLevel.TECHNOLOGY_MENTION:
            if product_name is None:
                raise ValueError("technology mentions require a product name")
        if self.evidence_level is TechnologyEvidenceLevel.PASSIVE_OBSERVATION:
            if product_name is None:
                raise ValueError("passive technology observations require a product name")
        if self.evidence_level is TechnologyEvidenceLevel.OBSERVED_VERSION:
            if product_name is None or product_version is None:
                raise ValueError("observed versions require product and version")


@dataclass(frozen=True, slots=True)
class PassiveObservationSnapshot:
    source_id: str
    source_record_key: str
    source_url: str
    asset: PassiveAsset
    observation_kind: PassiveObservationKind
    state: PassiveObservationState
    observed_at: datetime
    published_at: datetime
    modified_at: datetime
    confidence: float
    organization_link: OrganizationLink
    expires_at: datetime | None = None
    independence_key: str | None = None
    technology: TechnologyObservation | None = None
    port: int | None = None
    protocol: str | None = None
    active: bool = True
    historical_only: bool = False
    metadata_only: bool = True
    passive_only: bool = True
    active_probe_performed: bool = False
    credentials_used: bool = False
    access_control_bypassed: bool = False
    exploit_attempted: bool = False
    direct_validation_performed: bool = False
    vulnerability_applicability_assessed: bool = False
    exposure_verified: bool = False
    supersedes_record_key: str | None = None

    def __post_init__(self) -> None:
        _bounded(self.source_id, "source_id", maximum=200)
        _bounded(self.source_record_key, "source_record_key", maximum=500)
        _validate_source_url(self.source_url)
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        _validate_safety_flags(self)
        _normalize_timestamps(self)
        if self.modified_at < self.published_at:
            raise ValueError("modified_at cannot precede published_at")
        if self.published_at < self.observed_at:
            raise ValueError("published_at cannot precede observed_at")
        if self.expires_at is not None and self.expires_at < self.observed_at:
            raise ValueError("expires_at cannot precede observed_at")
        if self.state in _TERMINAL_STATES and self.active:
            raise ValueError("expired, retracted, or deleted observations cannot be active")
        if self.historical_only and self.state is PassiveObservationState.CURRENT:
            raise ValueError("historical-only observations cannot be current")
        _normalize_service_fields(self)
        if self.observation_kind in {
            PassiveObservationKind.PRODUCT,
            PassiveObservationKind.VERSION,
            PassiveObservationKind.TECHNOLOGY_MENTION,
        } and self.technology is None:
            raise ValueError("technology observations require technology metadata")
        if self.observation_kind is PassiveObservationKind.VERSION:
            if (
                self.technology is None
                or self.technology.evidence_level
                is not TechnologyEvidenceLevel.OBSERVED_VERSION
            ):
                raise ValueError("version observations require observed-version evidence")
        if self.independence_key is None:
            object.__setattr__(self, "independence_key", self.source_id)
        else:
            _bounded(self.independence_key, "independence_key", maximum=500)
        if self.supersedes_record_key is not None:
            _bounded(
                self.supersedes_record_key,
                "supersedes_record_key",
                maximum=500,
            )

    @property
    def observation_key(self) -> str:
        service = ""
        if self.port is not None and self.protocol is not None:
            service = f":{self.port}/{self.protocol}"
        return f"{self.asset.key}:{self.observation_kind.value}{service}"

    @property
    def can_support_exposure_conclusion(self) -> bool:
        return False


def normalize_asset(kind: PassiveAssetKind, value: str) -> str:
    if kind is PassiveAssetKind.DOMAIN:
        return normalize_domain(value)
    if kind is PassiveAssetKind.HOSTNAME:
        return normalize_hostname(value)
    if kind is PassiveAssetKind.IPV4:
        return normalize_ip(value, version=4)
    if kind is PassiveAssetKind.IPV6:
        return normalize_ip(value, version=6)
    if kind is PassiveAssetKind.CERTIFICATE:
        return normalize_certificate_fingerprint(value)
    if kind is PassiveAssetKind.ASN:
        return normalize_asn(value)
    if kind is PassiveAssetKind.CLOUD_RESOURCE:
        return normalize_cloud_resource(value)
    raise ValueError(f"unsupported passive asset kind: {kind}")


def _validate_source_url(value: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("source_url must be an absolute HTTPS URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("source_url cannot contain embedded credentials")


def _normalize_timestamps(snapshot: PassiveObservationSnapshot) -> None:
    for field_name in ("observed_at", "published_at", "modified_at", "expires_at"):
        value = getattr(snapshot, field_name)
        if value is not None:
            object.__setattr__(
                snapshot,
                field_name,
                require_aware_utc(value, field_name=field_name),
            )


def _normalize_service_fields(snapshot: PassiveObservationSnapshot) -> None:
    if snapshot.port is not None:
        object.__setattr__(snapshot, "port", normalize_port(snapshot.port))
    if snapshot.protocol is not None:
        object.__setattr__(snapshot, "protocol", normalize_protocol(snapshot.protocol))
    requires_service = snapshot.observation_kind in {
        PassiveObservationKind.PORT,
        PassiveObservationKind.SERVICE,
    }
    if requires_service and (snapshot.port is None or snapshot.protocol is None):
        raise ValueError("port and service observations require port and protocol")
    if (snapshot.port is None) != (snapshot.protocol is None):
        raise ValueError("port and protocol must be provided together")


def _validate_safety_flags(snapshot: PassiveObservationSnapshot) -> None:
    if not snapshot.metadata_only or not snapshot.passive_only:
        raise ValueError("passive exposure accepts passive metadata only")
    if any(
        (
            snapshot.active_probe_performed,
            snapshot.credentials_used,
            snapshot.access_control_bypassed,
            snapshot.exploit_attempted,
            snapshot.direct_validation_performed,
        )
    ):
        raise ValueError("active validation and access-control bypass are forbidden")
    if snapshot.vulnerability_applicability_assessed or snapshot.exposure_verified:
        raise ValueError("Lot 16 cannot assess vulnerability applicability or verify exposure")


def _bounded(value: str, field_name: str, *, maximum: int) -> None:
    if not value.strip() or len(value) > maximum:
        raise ValueError(f"{field_name} must be between 1 and {maximum} characters")


def _unique_text(values: tuple[str, ...], *, maximum: int) -> tuple[str, ...]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        if len(normalized) > maximum:
            raise ValueError(f"text value cannot exceed {maximum} characters")
        key = normalized.casefold()
        if key not in seen:
            seen.add(key)
            unique.append(normalized)
    return tuple(unique)

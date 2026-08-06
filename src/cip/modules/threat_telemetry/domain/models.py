from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlparse

from cip.modules.threat_telemetry.domain.normalization import (
    normalize_domain,
    normalize_email,
    normalize_hash,
    normalize_ip,
    normalize_url,
)
from cip.shared.kernel.time import require_aware_utc


class IndicatorType(StrEnum):
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    DOMAIN = "domain"
    URL = "url"
    FILE_HASH = "file_hash"
    CERTIFICATE_FINGERPRINT = "certificate_fingerprint"
    EMAIL_ADDRESS = "email_address"


class IndicatorState(StrEnum):
    MALICIOUS = "malicious"
    SUSPICIOUS = "suspicious"
    HISTORICAL = "historical"
    EXPIRED = "expired"
    SINKHOLED = "sinkholed"
    BENIGN = "benign"
    SHARED_INFRASTRUCTURE = "shared_infrastructure"
    UNKNOWN = "unknown"
    RETRACTED = "retracted"


class TelemetrySourceKind(StrEnum):
    STIX_TAXII = "stix_taxii"
    PHISHING_FEED = "phishing_feed"
    PASSIVE_DNS = "passive_dns"
    MALWARE_METADATA = "malware_metadata"
    CERTIFICATE_FEED = "certificate_feed"
    PROVIDER = "provider"
    OTHER = "other"


class SensorScope(StrEnum):
    GLOBAL = "global"
    REGIONAL = "regional"
    SECTOR = "sector"
    CUSTOMER_TENANT = "customer_tenant"
    PROVIDER_AGGREGATE = "provider_aggregate"
    UNKNOWN = "unknown"


class TelemetryRelationType(StrEnum):
    CAMPAIGN = "campaign"
    MALWARE_FAMILY = "malware_family"
    VULNERABILITY = "vulnerability"
    PHISHING_KIT = "phishing_kit"
    INFRASTRUCTURE = "infrastructure"


@dataclass(frozen=True, slots=True)
class TelemetryRelation:
    relation_type: TelemetryRelationType
    target_key: str
    confidence: float = 0.5

    def __post_init__(self) -> None:
        if not self.target_key.strip() or len(self.target_key) > 500:
            raise ValueError("relation target_key must be a bounded value")
        if not 0 <= self.confidence <= 1:
            raise ValueError("relation confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class IndicatorSnapshot:
    source_id: str
    source_kind: TelemetrySourceKind
    source_record_key: str
    source_url: str
    indicator_type: IndicatorType
    indicator_value: str
    state: IndicatorState
    published_at: datetime
    modified_at: datetime
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    expires_at: datetime | None = None
    independence_key: str | None = None
    sensor_scope: SensorScope = SensorScope.UNKNOWN
    confidence: float = 0.5
    source_precedence: int = 0
    active: bool = True
    shared_infrastructure: bool = False
    historical_only: bool = False
    metadata_only: bool = True
    binary_payload_present: bool = False
    direct_validation_performed: bool = False
    supersedes_record_key: str | None = None
    relations: tuple[TelemetryRelation, ...] = ()

    def __post_init__(self) -> None:
        _bounded(self.source_id, "source_id", maximum=200)
        _bounded(self.source_record_key, "source_record_key", maximum=500)
        parsed = urlparse(self.source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source_url must use http or https")
        if not self.metadata_only or self.binary_payload_present:
            raise ValueError("threat telemetry accepts metadata only and no binary payload")
        if self.direct_validation_performed:
            raise ValueError("direct indicator validation is forbidden")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if not 0 <= self.source_precedence <= 100:
            raise ValueError("source_precedence must be between 0 and 100")
        object.__setattr__(
            self,
            "indicator_value",
            normalize_indicator(self.indicator_type, self.indicator_value),
        )
        _normalize_timestamps(self)
        if self.modified_at < self.published_at:
            raise ValueError("modified_at cannot precede published_at")
        if (
            self.first_seen_at is not None
            and self.last_seen_at is not None
            and self.last_seen_at < self.first_seen_at
        ):
            raise ValueError("last_seen_at cannot precede first_seen_at")
        if (
            self.expires_at is not None
            and self.last_seen_at is not None
            and self.expires_at < self.last_seen_at
        ):
            raise ValueError("expires_at cannot precede last_seen_at")
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
        unique_relations = {
            (relation.relation_type, relation.target_key): relation
            for relation in self.relations
        }
        object.__setattr__(self, "relations", tuple(unique_relations.values()))

    @property
    def indicator_key(self) -> str:
        return f"{self.indicator_type.value}:{self.indicator_value}"

    @property
    def is_positive_detection(self) -> bool:
        return self.active and self.state in {
            IndicatorState.MALICIOUS,
            IndicatorState.SUSPICIOUS,
        }


@dataclass(frozen=True, slots=True)
class ReconciledIndicator:
    indicator_key: str
    indicator_type: IndicatorType
    indicator_value: str
    state: IndicatorState
    observed_states: tuple[IndicatorState, ...]
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    expires_at: datetime | None
    last_updated_at: datetime
    source_count: int
    independent_source_count: int
    active: bool
    shared_infrastructure: bool
    historical_only: bool
    has_conflict: bool
    relations: tuple[TelemetryRelation, ...]


def normalize_indicator(indicator_type: IndicatorType, value: str) -> str:
    if indicator_type is IndicatorType.IPV4:
        return normalize_ip(value, version=4)
    if indicator_type is IndicatorType.IPV6:
        return normalize_ip(value, version=6)
    if indicator_type is IndicatorType.DOMAIN:
        return normalize_domain(value)
    if indicator_type is IndicatorType.URL:
        return normalize_url(value)
    if indicator_type is IndicatorType.FILE_HASH:
        return normalize_hash(value)
    if indicator_type is IndicatorType.CERTIFICATE_FINGERPRINT:
        return normalize_hash(value, certificate=True)
    if indicator_type is IndicatorType.EMAIL_ADDRESS:
        return normalize_email(value)
    raise ValueError(f"unsupported indicator type: {indicator_type}")


def _normalize_timestamps(snapshot: IndicatorSnapshot) -> None:
    for field_name in (
        "published_at",
        "modified_at",
        "first_seen_at",
        "last_seen_at",
        "expires_at",
    ):
        value = getattr(snapshot, field_name)
        if value is not None:
            object.__setattr__(
                snapshot,
                field_name,
                require_aware_utc(value, field_name=field_name),
            )


def _bounded(value: str, field_name: str, *, maximum: int) -> None:
    if not value.strip() or len(value) > maximum:
        raise ValueError(f"{field_name} must be between 1 and {maximum} characters")

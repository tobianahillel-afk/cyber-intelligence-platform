from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ObservableType(StrEnum):
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    DOMAIN = "domain"
    URL = "url"
    FILE_HASH = "file_hash"
    CERTIFICATE_FINGERPRINT = "certificate_fingerprint"
    EMAIL_ADDRESS = "email_address"


class ProviderState(StrEnum):
    MALICIOUS = "malicious"
    SUSPICIOUS = "suspicious"
    HISTORICAL = "historical"
    EXPIRED = "expired"
    SINKHOLED = "sinkholed"
    BENIGN = "benign"
    SHARED_INFRASTRUCTURE = "shared_infrastructure"
    UNKNOWN = "unknown"
    RETRACTED = "retracted"


class RelationKind(StrEnum):
    CAMPAIGN = "campaign"
    MALWARE_FAMILY = "malware_family"
    VULNERABILITY = "vulnerability"
    PHISHING_KIT = "phishing_kit"
    INFRASTRUCTURE = "infrastructure"


class RelationMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: RelationKind
    target_key: str = Field(min_length=1, max_length=500)
    confidence: float = Field(default=0.5, ge=0, le=1)


class ThreatMetadataRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1, max_length=500)
    source_url: str = Field(pattern=r"^https?://", max_length=2_048)
    observable_type: ObservableType
    value: str = Field(min_length=1, max_length=2_048)
    state: ProviderState
    published_at: datetime
    modified_at: datetime
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    expires_at: datetime | None = None
    confidence: float = Field(default=0.5, ge=0, le=1)
    source_precedence: int = Field(default=0, ge=0, le=100)
    independence_key: str | None = Field(default=None, max_length=500)
    sensor_scope: str = Field(default="provider_aggregate", max_length=80)
    shared_infrastructure: bool = False
    historical_only: bool = False
    active: bool = True
    supersedes_record_key: str | None = Field(default=None, max_length=500)
    relations: tuple[RelationMetadata, ...] = ()
    binary_payload: str | None = None
    sample_download_url: str | None = None
    direct_validation: bool = False

    @model_validator(mode="after")
    def validate_metadata_only(self) -> ThreatMetadataRecord:
        if self.modified_at < self.published_at:
            raise ValueError("modified_at cannot precede published_at")
        if (
            self.first_seen_at is not None
            and self.last_seen_at is not None
            and self.last_seen_at < self.first_seen_at
        ):
            raise ValueError("last_seen_at cannot precede first_seen_at")
        if self.binary_payload is not None or self.sample_download_url is not None:
            raise ValueError("binary payloads and sample download URLs are forbidden")
        if self.direct_validation:
            raise ValueError("direct validation against the indicator is forbidden")
        return self


class StixTaxiiIndicatorRecord(ThreatMetadataRecord):
    stix_id: str = Field(min_length=1, max_length=500)
    pattern_type: str = Field(default="stix", pattern=r"^stix$")
    revoked: bool = False


class PhishingMetadataRecord(ThreatMetadataRecord):
    phishing_kit: str | None = Field(default=None, max_length=500)
    target_sector: str | None = Field(default=None, max_length=200)


class PassiveDnsMetadataRecord(ThreatMetadataRecord):
    observation_count: int = Field(default=1, ge=1)
    resolver_scope: str = Field(default="provider_aggregate", max_length=200)


class MalwareMetadataRecord(ThreatMetadataRecord):
    malware_family: str = Field(min_length=1, max_length=500)
    sample_available: bool = False

    @model_validator(mode="after")
    def reject_sample_availability(self) -> MalwareMetadataRecord:
        if self.sample_available:
            raise ValueError("malware samples are outside the platform scope")
        return self

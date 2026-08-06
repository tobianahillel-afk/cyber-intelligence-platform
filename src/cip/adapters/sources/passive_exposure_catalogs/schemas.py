from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProviderAssetKind(StrEnum):
    DOMAIN = "domain"
    HOSTNAME = "hostname"
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    CERTIFICATE = "certificate"
    ASN = "asn"
    CLOUD_RESOURCE = "cloud_resource"


class ProviderObservationKind(StrEnum):
    PASSIVE_DNS = "passive_dns"
    CERTIFICATE = "certificate"
    ASN = "asn"
    CLOUD = "cloud"
    SERVICE = "service"
    PORT = "port"
    PRODUCT = "product"
    VERSION = "version"
    TECHNOLOGY_MENTION = "technology_mention"


class ProviderObservationState(StrEnum):
    CURRENT = "current"
    HISTORICAL = "historical"
    EXPIRED = "expired"
    CORRECTED = "corrected"
    RETRACTED = "retracted"
    DELETED = "deleted"
    UNKNOWN = "unknown"


class ProviderAttributionRisk(StrEnum):
    SHARED_HOSTING = "shared_hosting"
    CDN = "cdn"
    RESELLER = "reseller"
    SUBSIDIARY = "subsidiary"
    ABANDONED_DOMAIN = "abandoned_domain"
    REASSIGNED_ADDRESS = "reassigned_address"


class ProviderTechnologyLevel(StrEnum):
    TECHNOLOGY_MENTION = "technology_mention"
    PASSIVE_OBSERVATION = "passive_observation"
    OBSERVED_VERSION = "observed_version"


_TERMINAL_STATES = {
    ProviderObservationState.EXPIRED,
    ProviderObservationState.RETRACTED,
    ProviderObservationState.DELETED,
}


class ProviderTechnologyMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_level: ProviderTechnologyLevel
    product_name: str = Field(min_length=1, max_length=300)
    product_version: str | None = Field(default=None, max_length=200)
    component_name: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def validate_version_level(self) -> ProviderTechnologyMetadata:
        if (
            self.evidence_level is ProviderTechnologyLevel.OBSERVED_VERSION
            and self.product_version is None
        ):
            raise ValueError("observed-version metadata requires a product version")
        return self


class PassiveAssetMetadataRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1, max_length=500)
    source_url: str = Field(pattern=r"^https://", max_length=2_048)
    asset_kind: ProviderAssetKind
    asset_value: str = Field(min_length=1, max_length=2_048)
    observation_kind: ProviderObservationKind
    state: ProviderObservationState
    observed_at: datetime
    published_at: datetime
    modified_at: datetime
    expires_at: datetime | None = None
    confidence: float = Field(default=0.5, ge=0, le=1)
    independence_key: str | None = Field(default=None, max_length=500)
    attribution_risks: tuple[ProviderAttributionRisk, ...] = ()
    technology: ProviderTechnologyMetadata | None = None
    port: int | None = Field(default=None, ge=1, le=65_535)
    protocol: str | None = Field(default=None, max_length=32)
    active: bool = True
    historical_only: bool = False
    supersedes_record_key: str | None = Field(default=None, max_length=500)
    binary_payload: str | None = None
    credential: str | None = None
    active_probe: bool = False
    direct_connection: bool = False
    authenticated_enumeration: bool = False
    access_control_bypass: bool = False
    exploit_attempt: bool = False
    applicability_assessed: bool = False
    exposure_verified: bool = False

    @model_validator(mode="after")
    def validate_passive_metadata_only(self) -> PassiveAssetMetadataRecord:
        _validate_source_url(self.source_url)
        if self.published_at < self.observed_at:
            raise ValueError("published_at cannot precede observed_at")
        if self.modified_at < self.published_at:
            raise ValueError("modified_at cannot precede published_at")
        if self.expires_at is not None and self.expires_at < self.observed_at:
            raise ValueError("expires_at cannot precede observed_at")
        if self.state in _TERMINAL_STATES and self.active:
            raise ValueError("expired, retracted, or deleted records cannot be active")
        if self.state is ProviderObservationState.HISTORICAL:
            if self.active:
                raise ValueError("historical records cannot be active")
            if not self.historical_only:
                raise ValueError("historical records must be historical-only")
        if self.historical_only and self.state is ProviderObservationState.CURRENT:
            raise ValueError("historical-only records cannot be current")
        if self.binary_payload is not None or self.credential is not None:
            raise ValueError("binary payloads and credentials are forbidden")
        if any(
            (
                self.active_probe,
                self.direct_connection,
                self.authenticated_enumeration,
                self.access_control_bypass,
                self.exploit_attempt,
            )
        ):
            raise ValueError("active or authenticated validation is forbidden")
        if self.applicability_assessed or self.exposure_verified:
            raise ValueError("applicability and exposure are not assessed in Lot 16")
        if (self.port is None) != (self.protocol is None):
            raise ValueError("port and protocol must be provided together")
        if self.observation_kind in {
            ProviderObservationKind.SERVICE,
            ProviderObservationKind.PORT,
        } and self.port is None:
            raise ValueError("service observations require port and protocol")
        if self.observation_kind in {
            ProviderObservationKind.PRODUCT,
            ProviderObservationKind.VERSION,
            ProviderObservationKind.TECHNOLOGY_MENTION,
        } and self.technology is None:
            raise ValueError("technology observations require technology metadata")
        if self.observation_kind is ProviderObservationKind.VERSION:
            if (
                self.technology is None
                or self.technology.evidence_level
                is not ProviderTechnologyLevel.OBSERVED_VERSION
            ):
                raise ValueError("version observations require observed-version metadata")
        return self


class PassiveExposureMetadataRecord(PassiveAssetMetadataRecord):
    provider_asset_id: str | None = Field(default=None, max_length=500)


class TechnographicMetadataRecord(PassiveAssetMetadataRecord):
    technology: ProviderTechnologyMetadata


class CloudAssetMetadataRecord(PassiveAssetMetadataRecord):
    asset_kind: ProviderAssetKind = ProviderAssetKind.CLOUD_RESOURCE
    cloud_provider: str = Field(min_length=1, max_length=100)
    tenant_shared: bool = False

    @model_validator(mode="after")
    def validate_cloud_identity_and_tenancy(self) -> CloudAssetMetadataRecord:
        if self.asset_kind is not ProviderAssetKind.CLOUD_RESOURCE:
            raise ValueError("cloud metadata requires a cloud-resource asset")
        provider = self.cloud_provider.strip().casefold()
        if not provider:
            raise ValueError("cloud_provider cannot be blank")
        namespace = self.asset_value.partition(":")[0].casefold()
        if namespace != provider:
            raise ValueError("cloud resource namespace must match cloud_provider")
        self.cloud_provider = provider
        has_shared_risk = (
            ProviderAttributionRisk.SHARED_HOSTING in self.attribution_risks
        )
        if self.tenant_shared and not has_shared_risk:
            raise ValueError(
                "shared cloud tenancy requires shared-hosting attribution risk"
            )
        return self


def _validate_source_url(value: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("source_url must be an absolute HTTPS URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("source_url cannot contain embedded credentials")

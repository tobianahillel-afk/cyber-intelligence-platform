from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cip.shared.kernel.time import require_aware_utc


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
    REGISTRATION = "registration"
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
_TECHNOLOGY_KINDS = {
    ProviderObservationKind.PRODUCT,
    ProviderObservationKind.VERSION,
    ProviderObservationKind.TECHNOLOGY_MENTION,
}
_SERVICE_KINDS = {
    ProviderObservationKind.SERVICE,
    ProviderObservationKind.PORT,
}


class ProviderTechnologyMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    evidence_level: ProviderTechnologyLevel
    product_name: str = Field(min_length=1, max_length=300)
    product_version: str | None = Field(default=None, min_length=1, max_length=200)
    component_name: str | None = Field(default=None, min_length=1, max_length=300)

    @model_validator(mode="after")
    def validate_version_level(self) -> ProviderTechnologyMetadata:
        if (
            self.evidence_level is ProviderTechnologyLevel.OBSERVED_VERSION
            and self.product_version is None
        ):
            raise ValueError("observed-version metadata requires a product version")
        return self


class PassiveAssetMetadataRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

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
    independence_key: str | None = Field(default=None, min_length=1, max_length=500)
    attribution_risks: tuple[ProviderAttributionRisk, ...] = ()
    technology: ProviderTechnologyMetadata | None = None
    port: int | None = Field(default=None, ge=1, le=65_535)
    protocol: str | None = Field(default=None, min_length=1, max_length=32)
    active: bool = True
    historical_only: bool = False
    supersedes_record_key: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )
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
        _normalize_timestamps(self)
        _validate_source_url(self.source_url)
        _validate_timestamp_order(self)
        _validate_record_state(self)
        _validate_passive_safety(self)
        _validate_service_metadata(self)
        _validate_technology_metadata(self)
        return self


class PassiveExposureMetadataRecord(PassiveAssetMetadataRecord):
    provider_asset_id: str | None = Field(default=None, min_length=1, max_length=500)


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
        provider = self.cloud_provider.casefold()
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


def _normalize_timestamps(record: PassiveAssetMetadataRecord) -> None:
    record.observed_at = require_aware_utc(
        record.observed_at,
        field_name="observed_at",
    )
    record.published_at = require_aware_utc(
        record.published_at,
        field_name="published_at",
    )
    record.modified_at = require_aware_utc(
        record.modified_at,
        field_name="modified_at",
    )
    if record.expires_at is not None:
        record.expires_at = require_aware_utc(
            record.expires_at,
            field_name="expires_at",
        )


def _validate_timestamp_order(record: PassiveAssetMetadataRecord) -> None:
    if record.published_at < record.observed_at:
        raise ValueError("published_at cannot precede observed_at")
    if record.modified_at < record.published_at:
        raise ValueError("modified_at cannot precede published_at")
    if record.expires_at is not None and record.expires_at < record.observed_at:
        raise ValueError("expires_at cannot precede observed_at")


def _validate_record_state(record: PassiveAssetMetadataRecord) -> None:
    if record.state in _TERMINAL_STATES and record.active:
        raise ValueError("expired, retracted, or deleted records cannot be active")
    if record.state is ProviderObservationState.HISTORICAL:
        if record.active:
            raise ValueError("historical records cannot be active")
        if not record.historical_only:
            raise ValueError("historical records must be historical-only")
    if record.historical_only and record.state is ProviderObservationState.CURRENT:
        raise ValueError("historical-only records cannot be current")


def _validate_passive_safety(record: PassiveAssetMetadataRecord) -> None:
    if record.binary_payload is not None or record.credential is not None:
        raise ValueError("binary payloads and credentials are forbidden")
    if any(
        (
            record.active_probe,
            record.direct_connection,
            record.authenticated_enumeration,
            record.access_control_bypass,
            record.exploit_attempt,
        )
    ):
        raise ValueError("active or authenticated validation is forbidden")
    if record.applicability_assessed or record.exposure_verified:
        raise ValueError("applicability and exposure are not assessed in Lot 16")


def _validate_service_metadata(record: PassiveAssetMetadataRecord) -> None:
    if (record.port is None) != (record.protocol is None):
        raise ValueError("port and protocol must be provided together")
    if record.observation_kind in _SERVICE_KINDS and record.port is None:
        raise ValueError("service observations require port and protocol")


def _validate_technology_metadata(record: PassiveAssetMetadataRecord) -> None:
    if record.observation_kind in _TECHNOLOGY_KINDS and record.technology is None:
        raise ValueError("technology observations require technology metadata")
    if (
        record.observation_kind is ProviderObservationKind.VERSION
        and (
            record.technology is None
            or record.technology.evidence_level
            is not ProviderTechnologyLevel.OBSERVED_VERSION
        )
    ):
        raise ValueError("version observations require observed-version metadata")


def _validate_source_url(value: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("source_url must be an absolute HTTPS URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("source_url cannot contain embedded credentials")

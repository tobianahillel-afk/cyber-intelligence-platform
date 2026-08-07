from __future__ import annotations

from datetime import datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cip.modules.vulnerability_applicability.domain.enums import (
    AdvisoryRevisionState,
    MatchPrecision,
    SupportStatus,
    VersionBoundaryKind,
    VersionScheme,
)
from cip.shared.kernel.time import require_aware_utc


class ProviderProduct(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    vendor: str = Field(min_length=1, max_length=300)
    product: str = Field(min_length=1, max_length=300)
    component: str | None = Field(default=None, min_length=1, max_length=300)
    edition: str | None = Field(default=None, min_length=1, max_length=300)
    ecosystem: str | None = Field(default=None, min_length=1, max_length=100)
    platform: str | None = Field(default=None, min_length=1, max_length=200)
    identifiers: tuple[str, ...] = ()
    support_status: SupportStatus = SupportStatus.UNKNOWN
    end_of_support_at: datetime | None = None

    @model_validator(mode="after")
    def normalize_end_of_support(self) -> ProviderProduct:
        if self.end_of_support_at is not None:
            self.end_of_support_at = require_aware_utc(
                self.end_of_support_at,
                field_name="end_of_support_at",
            )
        return self


class ProviderVersionBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: VersionBoundaryKind
    version: str = Field(min_length=1, max_length=200)
    inclusive: bool


class ProviderAffectedRange(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    product: ProviderProduct
    scheme: VersionScheme
    boundaries: tuple[ProviderVersionBoundary, ...] = Field(min_length=1)
    vulnerable: bool = True
    backported_fix: bool = False
    branch: str | None = Field(default=None, min_length=1, max_length=200)
    precision: MatchPrecision = MatchPrecision.PRODUCT


class ProviderAdvisoryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    record_id: str = Field(min_length=1, max_length=500)
    advisory_id: str = Field(min_length=1, max_length=300)
    source_url: str = Field(pattern=r"^https://", max_length=2_048)
    state: AdvisoryRevisionState
    published_at: datetime
    modified_at: datetime
    vulnerabilities: tuple[str, ...] = Field(min_length=1)
    affected_ranges: tuple[ProviderAffectedRange, ...] = ()
    title: str | None = Field(default=None, min_length=1, max_length=500)
    fixed_versions: tuple[str, ...] = ()
    workarounds: tuple[str, ...] = ()
    supersedes_record_key: str | None = Field(default=None, min_length=1, max_length=500)
    metadata_only: bool = True
    binary_payload: str | None = None
    credential: str | None = None
    active_probe: bool = False
    direct_connection: bool = False
    authenticated_enumeration: bool = False
    access_control_bypass: bool = False
    exploit_attempt: bool = False
    exposure_verified: bool = False

    @model_validator(mode="after")
    def validate_metadata_only_record(self) -> ProviderAdvisoryRecord:
        self.published_at = require_aware_utc(
            self.published_at,
            field_name="published_at",
        )
        self.modified_at = require_aware_utc(
            self.modified_at,
            field_name="modified_at",
        )
        if self.modified_at < self.published_at:
            raise ValueError("modified_at cannot precede published_at")
        _validate_source_url(self.source_url)
        if not self.metadata_only:
            raise ValueError("vendor advisory records must remain metadata-only")
        if self.binary_payload is not None or self.credential is not None:
            raise ValueError("binary payloads and credentials are forbidden")
        if any(
            (
                self.active_probe,
                self.direct_connection,
                self.authenticated_enumeration,
                self.access_control_bypass,
                self.exploit_attempt,
                self.exposure_verified,
            )
        ):
            raise ValueError("active validation and exposure verification are forbidden")
        return self


def _validate_source_url(value: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("source_url must be an absolute HTTPS URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("source_url cannot contain embedded credentials")

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PublicIncidentKind(StrEnum):
    RANSOMWARE = "ransomware"
    DATA_BREACH = "data_breach"
    EXTORTION = "extortion"
    BUSINESS_EMAIL_COMPROMISE = "business_email_compromise"
    SERVICE_DISRUPTION = "service_disruption"
    SUPPLY_CHAIN = "supply_chain"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    MALWARE = "malware"
    UNKNOWN = "unknown"


class OfficialDisclosureKind(StrEnum):
    COMPANY_CONFIRMATION = "company_confirmation"
    REGULATOR_NOTICE = "regulator_notice"
    CERT_NOTICE = "cert_notice"
    DENIAL = "denial"
    CORRECTION = "correction"
    RETRACTION = "retraction"


class ReportKind(StrEnum):
    MEDIA_REPORT = "media_report"
    RESEARCHER_REPORT = "researcher_report"
    PROVIDER_STATEMENT = "provider_statement"


class OrganizationReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claimed_name: str = Field(min_length=1, max_length=500)
    exact_registration_id: str | None = Field(default=None, max_length=200)
    exact_organization_id: str | None = Field(default=None, max_length=100)


class OfficialIncidentDisclosure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1, max_length=500)
    incident_key: str = Field(min_length=1, max_length=500)
    source_url: str = Field(pattern=r"^https?://", max_length=2_048)
    disclosure_kind: OfficialDisclosureKind
    incident_kind: PublicIncidentKind = PublicIncidentKind.UNKNOWN
    title: str = Field(min_length=1, max_length=1_000)
    summary: str = Field(min_length=1, max_length=8_000)
    organization: OrganizationReference | None = None
    published_at: datetime
    modified_at: datetime
    occurrence_start_at: datetime | None = None
    occurrence_end_at: datetime | None = None
    discovered_at: datetime | None = None
    confirmed_at: datetime | None = None
    supersedes_record_id: str | None = Field(default=None, max_length=500)
    historical_only: bool = False

    @model_validator(mode="after")
    def validate_chronology(self) -> OfficialIncidentDisclosure:
        if self.modified_at < self.published_at:
            raise ValueError("modified_at cannot precede published_at")
        if (
            self.occurrence_start_at is not None
            and self.occurrence_end_at is not None
            and self.occurrence_end_at < self.occurrence_start_at
        ):
            raise ValueError("occurrence_end_at cannot precede occurrence_start_at")
        confirms = self.disclosure_kind in {
            OfficialDisclosureKind.COMPANY_CONFIRMATION,
            OfficialDisclosureKind.REGULATOR_NOTICE,
            OfficialDisclosureKind.CERT_NOTICE,
        }
        if self.confirmed_at is not None and not confirms:
            raise ValueError("confirmed_at requires an official confirmation disclosure")
        return self


class PublicIncidentReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1, max_length=500)
    incident_key: str = Field(min_length=1, max_length=500)
    source_url: str = Field(pattern=r"^https?://", max_length=2_048)
    report_kind: ReportKind
    incident_kind: PublicIncidentKind = PublicIncidentKind.UNKNOWN
    title: str = Field(min_length=1, max_length=1_000)
    summary: str = Field(min_length=1, max_length=8_000)
    organization: OrganizationReference | None = None
    published_at: datetime
    modified_at: datetime
    occurrence_start_at: datetime | None = None
    occurrence_end_at: datetime | None = None
    discovered_at: datetime | None = None
    syndication_group: str | None = Field(default=None, max_length=500)
    confidence: float = Field(default=0.6, ge=0, le=1)
    historical_only: bool = False

    @model_validator(mode="after")
    def validate_chronology(self) -> PublicIncidentReport:
        if self.modified_at < self.published_at:
            raise ValueError("modified_at cannot precede published_at")
        return self


class RansomwareMetadataRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1, max_length=500)
    incident_key: str = Field(min_length=1, max_length=500)
    provider_record_url: str = Field(pattern=r"^https?://", max_length=2_048)
    provider_name: str = Field(min_length=1, max_length=200)
    claimed_victim_name: str = Field(min_length=1, max_length=500)
    group_name: str | None = Field(default=None, max_length=200)
    claim_title: str = Field(min_length=1, max_length=1_000)
    claim_summary: str = Field(min_length=1, max_length=4_000)
    published_at: datetime
    modified_at: datetime
    occurrence_start_at: datetime | None = None
    syndication_group: str | None = Field(default=None, max_length=500)
    historical_only: bool = False

    @model_validator(mode="after")
    def validate_metadata_only(self) -> RansomwareMetadataRecord:
        if self.modified_at < self.published_at:
            raise ValueError("modified_at cannot precede published_at")
        hostname = self.provider_record_url.casefold()
        if ".onion" in hostname:
            raise ValueError("threat-actor onion URLs are forbidden")
        return self

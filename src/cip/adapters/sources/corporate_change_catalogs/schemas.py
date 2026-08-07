from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_EXCERPT_LENGTH = 500


class ProviderChangeKind(StrEnum):
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


class OfficialChangeKind(StrEnum):
    CONFIRMATION = "confirmation"
    DISPUTE = "dispute"
    CORRECTION = "correction"
    RETRACTION = "retraction"


class ReportChangeKind(StrEnum):
    REPORT = "report"
    SPECULATION = "speculation"
    CORRECTION = "correction"
    RETRACTION = "retraction"


class OrganizationReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claimed_name: str = Field(min_length=1, max_length=500)
    exact_organization_id: str | None = Field(default=None, max_length=100)
    registration_id: str | None = Field(default=None, max_length=200)


class OfficialChangeDisclosure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1, max_length=500)
    article_id: str = Field(min_length=1, max_length=500)
    event_key: str = Field(min_length=1, max_length=500)
    source_url: str = Field(pattern=r"^https?://", max_length=2_048)
    change_kind: ProviderChangeKind
    disclosure_kind: OfficialChangeKind
    title: str = Field(min_length=1, max_length=1_000)
    excerpt: str = Field(min_length=1, max_length=MAX_EXCERPT_LENGTH)
    organization: OrganizationReference | None = None
    published_at: datetime
    modified_at: datetime
    event_at: datetime | None = None
    expires_at: datetime | None = None
    supersedes_record_id: str | None = Field(default=None, max_length=500)
    historical_only: bool = False

    @model_validator(mode="after")
    def validate_chronology(self) -> OfficialChangeDisclosure:
        _validate_chronology(
            self.published_at,
            self.modified_at,
            self.expires_at,
        )
        return self


class PublicChangeReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1, max_length=500)
    article_id: str = Field(min_length=1, max_length=500)
    event_key: str = Field(min_length=1, max_length=500)
    source_url: str = Field(pattern=r"^https?://", max_length=2_048)
    source_class: str = Field(pattern=r"^(media|analyst)$")
    change_kind: ProviderChangeKind
    report_kind: ReportChangeKind
    title: str = Field(min_length=1, max_length=1_000)
    excerpt: str = Field(min_length=1, max_length=MAX_EXCERPT_LENGTH)
    organization: OrganizationReference | None = None
    published_at: datetime
    modified_at: datetime
    event_at: datetime | None = None
    expires_at: datetime | None = None
    syndication_group: str | None = Field(default=None, max_length=500)
    confidence: float = Field(default=0.6, ge=0, le=1)
    supersedes_record_id: str | None = Field(default=None, max_length=500)
    historical_only: bool = False

    @model_validator(mode="after")
    def validate_chronology(self) -> PublicChangeReport:
        _validate_chronology(
            self.published_at,
            self.modified_at,
            self.expires_at,
        )
        return self


def _validate_chronology(
    published_at: datetime,
    modified_at: datetime,
    expires_at: datetime | None,
) -> None:
    if modified_at < published_at:
        raise ValueError("modified_at cannot precede published_at")
    if expires_at is not None and expires_at < published_at:
        raise ValueError("expires_at cannot precede published_at")

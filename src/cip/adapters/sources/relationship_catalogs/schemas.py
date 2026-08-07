from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_EXCERPT_LENGTH = 500


class ProviderRelationshipRole(StrEnum):
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


class ProviderEvidenceClass(StrEnum):
    CLAIMED = "claimed"
    OBSERVED = "observed"
    HISTORICAL = "historical"
    INFERRED = "inferred"


class ProviderClaimKind(StrEnum):
    ASSERTION = "assertion"
    DISPUTE = "dispute"
    CORRECTION = "correction"
    RETRACTION = "retraction"


class ProviderSourceKind(StrEnum):
    OFFICIAL_DISCLOSURE = "official_disclosure"
    CASE_STUDY = "case_study"
    PARTNER_DIRECTORY = "partner_directory"
    CERTIFICATE = "certificate"
    PASSIVE_OBSERVATION = "passive_observation"
    REGULATORY_FILING = "regulatory_filing"
    LICENSED_METADATA = "licensed_metadata"
    OTHER = "other"


class OrganizationReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claimed_name: str = Field(min_length=1, max_length=500)
    exact_organization_id: str | None = Field(default=None, max_length=100)


class PublicRelationshipRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1, max_length=500)
    relationship_key: str = Field(min_length=1, max_length=500)
    source_url: str = Field(pattern=r"^https?://", max_length=2_048)
    source_kind: ProviderSourceKind
    role: ProviderRelationshipRole
    evidence_class: ProviderEvidenceClass
    claim_kind: ProviderClaimKind = ProviderClaimKind.ASSERTION
    title: str = Field(min_length=1, max_length=1_000)
    excerpt: str = Field(min_length=1, max_length=MAX_EXCERPT_LENGTH)
    source_organization: OrganizationReference
    target_organization: OrganizationReference
    published_at: datetime
    modified_at: datetime
    observed_at: datetime
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    expires_at: datetime | None = None
    product_context: str | None = Field(default=None, max_length=500)
    service_context: str | None = Field(default=None, max_length=500)
    independence_key: str | None = Field(default=None, max_length=500)
    confidence: float = Field(default=0.6, ge=0, le=1)
    historical_only: bool = False
    supersedes_record_id: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_relationship(self) -> PublicRelationshipRecord:
        if self.modified_at < self.published_at:
            raise ValueError("modified_at cannot precede published_at")
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("valid_until cannot precede valid_from")
        if self.expires_at and self.expires_at < self.published_at:
            raise ValueError("expires_at cannot precede published_at")
        if (
            self.source_organization.exact_organization_id
            and self.source_organization.exact_organization_id
            == self.target_organization.exact_organization_id
        ):
            raise ValueError("relationship endpoints must be different organizations")
        return self

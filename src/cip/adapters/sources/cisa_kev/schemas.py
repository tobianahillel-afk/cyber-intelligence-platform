from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CisaKevVulnerability(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    cve_id: str = Field(alias="cveID", pattern=r"^CVE-\d{4}-\d{4,}$")
    vendor_project: str = Field(alias="vendorProject", min_length=1, max_length=300)
    product: str = Field(min_length=1, max_length=500)
    vulnerability_name: str = Field(alias="vulnerabilityName", min_length=1, max_length=500)
    date_added: date = Field(alias="dateAdded")
    short_description: str = Field(alias="shortDescription", min_length=1, max_length=8_000)
    required_action: str = Field(alias="requiredAction", min_length=1, max_length=8_000)
    due_date: date = Field(alias="dueDate")
    known_ransomware_campaign_use: str = Field(
        alias="knownRansomwareCampaignUse",
        min_length=1,
        max_length=50,
    )
    notes: str = Field(default="", max_length=8_000)
    cwes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self) -> CisaKevVulnerability:
        if self.due_date < self.date_added:
            raise ValueError("dueDate cannot precede dateAdded")
        return self


class CisaKevCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    title: str = Field(min_length=1, max_length=500)
    catalog_version: str = Field(alias="catalogVersion", min_length=1, max_length=100)
    date_released: datetime = Field(alias="dateReleased")
    count: int = Field(ge=0)
    vulnerabilities: list[CisaKevVulnerability]

    @model_validator(mode="after")
    def validate_count(self) -> CisaKevCatalog:
        if self.count != len(self.vulnerabilities):
            raise ValueError("catalog count does not match vulnerabilities length")
        if self.date_released.tzinfo is None or self.date_released.utcoffset() is None:
            raise ValueError("dateReleased must be timezone-aware")
        return self

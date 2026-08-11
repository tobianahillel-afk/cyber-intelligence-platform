from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class CordisOrganizationRecord(BaseModel):
    """One observed row from CORDIS Horizon `organization.csv`."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    projectID: str
    projectAcronym: str
    organisationID: str
    vatNumber: str
    name: str
    shortName: str
    SME: str
    activityType: str
    street: str
    postCode: str
    city: str
    country: str
    nutsCode: str
    geolocation: str
    organizationURL: str
    contactForm: str
    contentUpdateDate: str
    rcn: str
    order: str
    role: str
    ecContribution: str
    netEcContribution: str
    totalCost: str
    endOfParticipation: str
    active: str

    @field_validator("projectID", "organisationID", "name")
    @classmethod
    def _required_identity(cls, value: str) -> str:
        if not value:
            raise ValueError("CORDIS funding identity field cannot be blank")
        return value

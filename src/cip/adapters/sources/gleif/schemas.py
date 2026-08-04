from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class GleifName(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    language: str | None = None
    type: str | None = None


class GleifAddress(BaseModel):
    model_config = ConfigDict(extra="ignore")

    language: str | None = None
    addressLines: list[str] = Field(default_factory=list)
    addressNumber: str | None = None
    addressNumberWithinBuilding: str | None = None
    mailRouting: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None
    postalCode: str | None = None

    def formatted(self) -> str | None:
        values = [
            *self.addressLines,
            self.addressNumber,
            self.addressNumberWithinBuilding,
            self.mailRouting,
            self.postalCode,
            self.city,
            self.region,
            self.country,
        ]
        compact = [value.strip() for value in values if value and value.strip()]
        return ", ".join(dict.fromkeys(compact)) or None


class GleifLegalForm(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    other: str | None = None

    def label(self) -> str | None:
        return self.other or self.id


class GleifRegistrationAuthority(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    other: str | None = None


class GleifEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    legalName: GleifName
    otherNames: list[GleifName] = Field(default_factory=list)
    legalAddress: GleifAddress | None = None
    headquartersAddress: GleifAddress | None = None
    registeredAt: GleifRegistrationAuthority | None = None
    registeredAs: str | None = None
    jurisdiction: str | None = None
    category: str | None = None
    legalForm: GleifLegalForm | None = None
    status: str | None = None
    creationDate: date | None = None


class GleifRegistration(BaseModel):
    model_config = ConfigDict(extra="ignore")

    initialRegistrationDate: datetime | None = None
    lastUpdateDate: datetime | None = None
    status: str | None = None
    nextRenewalDate: datetime | None = None
    managingLou: str | None = None
    corroborationLevel: str | None = None


class GleifAttributes(BaseModel):
    model_config = ConfigDict(extra="ignore")

    lei: str
    entity: GleifEntity
    registration: GleifRegistration | None = None


class GleifRecordData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str
    id: str
    attributes: GleifAttributes


class GleifRecordResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    data: GleifRecordData


class GleifRelationshipNode(BaseModel):
    model_config = ConfigDict(extra="ignore")

    nodeID: str
    nodeType: str | None = None


class GleifRelationship(BaseModel):
    model_config = ConfigDict(extra="ignore")

    startNode: GleifRelationshipNode
    endNode: GleifRelationshipNode
    relationshipType: str | None = None
    relationshipStatus: str | None = None


class GleifRelationshipPeriod(BaseModel):
    model_config = ConfigDict(extra="ignore")

    startDate: datetime | None = None
    endDate: datetime | None = None
    periodType: str | None = None


class GleifRelationshipAttributes(BaseModel):
    model_config = ConfigDict(extra="ignore")

    relationship: GleifRelationship
    periods: list[GleifRelationshipPeriod] = Field(default_factory=list)


class GleifRelationshipData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str
    id: str
    attributes: GleifRelationshipAttributes


class GleifRelationshipResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    data: GleifRelationshipData | None = None

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

DnsName = Annotated[str, StringConstraints(min_length=1, max_length=253)]


class CloudflareDnsQuestion(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: DnsName
    record_type: int = Field(alias="type", ge=1, le=65_535)


class CloudflareDnsAnswer(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: DnsName
    record_type: int = Field(alias="type", ge=1, le=65_535)
    ttl: int = Field(alias="TTL", ge=0, le=2_592_000)
    data: str = Field(min_length=1, max_length=2_048)


class CloudflareDnsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    status: int = Field(alias="Status", ge=0, le=65_535)
    questions: list[CloudflareDnsQuestion] = Field(
        default_factory=list,
        alias="Question",
        max_length=64,
    )
    answers: list[CloudflareDnsAnswer] = Field(
        default_factory=list,
        alias="Answer",
        max_length=512,
    )


class CertSpotterCertificate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, max_length=500)
    tbs_sha256: str = Field(pattern=r"^[0-9A-Fa-f]{64}$")
    dns_names: list[DnsName] = Field(default_factory=list, max_length=1_000)
    not_before: datetime | None = None
    not_after: datetime | None = None

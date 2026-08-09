from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CloudflareDnsQuestion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    type: int


class CloudflareDnsAnswer(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    type: int
    TTL: int = Field(ge=0)
    data: str


class CloudflareDnsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    Status: int
    Question: list[CloudflareDnsQuestion] = Field(default_factory=list)
    Answer: list[CloudflareDnsAnswer] = Field(default_factory=list)


class CertSpotterCertificate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1)
    tbs_sha256: str = Field(min_length=1)
    dns_names: list[str] = Field(default_factory=list)
    not_before: datetime | None = None
    not_after: datetime | None = None

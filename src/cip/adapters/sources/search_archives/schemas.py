from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BraveWebResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=1, max_length=1_000)
    url: str = Field(min_length=1, max_length=4_096)
    description: str = Field(default="No snippet supplied", max_length=4_000)


class BraveWebResults(BaseModel):
    model_config = ConfigDict(extra="ignore")

    results: list[BraveWebResult] = Field(default_factory=list, max_length=20)


class BraveSearchResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    web: BraveWebResults | None = None


class ArchiveCapture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: str = Field(pattern=r"^\d{14}$")
    original: str = Field(min_length=1, max_length=4_096)
    mimetype: str = Field(min_length=1, max_length=200)
    statuscode: str = Field(pattern=r"^\d{3}$")
    digest: str = Field(min_length=1, max_length=200)
    length: int = Field(ge=0, le=1_000_000_000)

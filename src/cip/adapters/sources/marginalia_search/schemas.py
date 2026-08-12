from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MarginaliaSearchResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    url: str = Field(min_length=1, max_length=4_096)
    title: str = Field(default="Untitled result", max_length=1_000)
    description: str = Field(default="", max_length=4_000)


class MarginaliaSearchResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    query: str = Field(min_length=1, max_length=2_000)
    license: str = Field(default="", max_length=500)
    results: list[MarginaliaSearchResult] = Field(default_factory=list, max_length=100)

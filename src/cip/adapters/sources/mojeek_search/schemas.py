from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MojeekWebResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    url: str = Field(min_length=1, max_length=4_096)
    title: str = Field(min_length=1, max_length=1_000)
    desc: str = Field(default="No snippet supplied", max_length=4_000)


class MojeekResponseBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str = Field(min_length=1, max_length=200)
    results: list[MojeekWebResult] = Field(default_factory=list, max_length=20)


class MojeekSearchResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    response: MojeekResponseBody

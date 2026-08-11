from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CrossrefWork(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True, str_strip_whitespace=True)

    doi: str = Field(alias="DOI", min_length=1, max_length=300)
    title: tuple[str, ...] = Field(default_factory=tuple, max_length=8)
    type: str = Field(min_length=1, max_length=100)
    url: str = Field(alias="URL", min_length=1, max_length=2_000)


class CrossrefWorksMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: tuple[CrossrefWork, ...] = Field(default_factory=tuple, max_length=20)


class CrossrefWorksResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    status: str = Field(min_length=1, max_length=50)
    message_type: str = Field(alias="message-type", min_length=1, max_length=100)
    message: CrossrefWorksMessage

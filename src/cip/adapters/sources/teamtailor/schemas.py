from __future__ import annotations

from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class TeamtailorJobAttributes(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=1, max_length=500)
    body: str = Field(default="", max_length=500_000)
    pitch: str = Field(default="", max_length=100_000)
    remote_status: str | None = Field(default=None, alias="remote-status", max_length=100)
    employment_type: str | None = Field(
        default=None,
        alias="employment-type",
        max_length=100,
    )
    created_at: datetime = Field(alias="created-at")

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Teamtailor job title cannot be empty")
        return normalized

    @field_validator("created_at")
    @classmethod
    def require_aware_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created-at must be timezone-aware")
        return value


class TeamtailorResourceLinks(BaseModel):
    model_config = ConfigDict(extra="ignore")

    self_url: AnyHttpUrl | None = Field(default=None, alias="self")


class TeamtailorJobResource(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, max_length=200)
    type: str = Field(pattern=r"^jobs$")
    attributes: TeamtailorJobAttributes
    links: TeamtailorResourceLinks = Field(default_factory=TeamtailorResourceLinks)


class TeamtailorPaginationLinks(BaseModel):
    model_config = ConfigDict(extra="ignore")

    next: AnyHttpUrl | None = None


class TeamtailorJobsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    data: list[TeamtailorJobResource] = Field(default_factory=list, max_length=10_000)
    links: TeamtailorPaginationLinks = Field(default_factory=TeamtailorPaginationLinks)

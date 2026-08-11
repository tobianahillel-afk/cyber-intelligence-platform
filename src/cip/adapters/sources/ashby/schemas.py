from __future__ import annotations

from datetime import datetime
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class AshbySecondaryLocation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    location: str | None = Field(default=None, max_length=500)


class AshbyJobPosting(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=1, max_length=500)
    location: str | None = Field(default=None, max_length=500)
    secondary_locations: list[AshbySecondaryLocation] = Field(
        default_factory=list,
        alias="secondaryLocations",
        max_length=100,
    )
    department: str | None = Field(default=None, max_length=500)
    team: str | None = Field(default=None, max_length=500)
    is_listed: bool = Field(alias="isListed")
    is_remote: bool = Field(alias="isRemote")
    workplace_type: str | None = Field(default=None, alias="workplaceType", max_length=50)
    description_plain: str = Field(default="", alias="descriptionPlain", max_length=500_000)
    published_at: datetime = Field(alias="publishedAt")
    employment_type: str | None = Field(default=None, alias="employmentType", max_length=50)
    job_url: AnyHttpUrl = Field(alias="jobUrl")

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Ashby job title cannot be empty")
        return normalized

    @field_validator("published_at")
    @classmethod
    def require_aware_published_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("publishedAt must be timezone-aware")
        return value

    @property
    def source_job_id(self) -> str:
        path = urlsplit(str(self.job_url)).path.rstrip("/")
        identifier = path.rsplit("/", maxsplit=1)[-1]
        if not identifier:
            raise ValueError("Ashby jobUrl must contain a job identifier")
        return identifier

    def display_location(self) -> str:
        locations: list[str] = []
        if self.location and self.location.strip():
            locations.append(self.location.strip())
        locations.extend(
            item.location.strip()
            for item in self.secondary_locations
            if item.location and item.location.strip()
        )
        return "; ".join(dict.fromkeys(locations)) or "Unspecified"


class AshbyJobBoardResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    api_version: str = Field(alias="apiVersion", pattern=r"^1$")
    jobs: list[AshbyJobPosting] = Field(default_factory=list, max_length=10_000)

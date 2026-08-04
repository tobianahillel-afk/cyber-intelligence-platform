from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class GreenhouseLocation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=500)


class GreenhouseNamedNode(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    name: str = Field(min_length=1, max_length=500)


class GreenhouseJob(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int = Field(gt=0)
    internal_job_id: int | None = None
    title: str = Field(min_length=1, max_length=500)
    updated_at: datetime
    absolute_url: AnyHttpUrl
    location: GreenhouseLocation
    language: str | None = Field(default=None, max_length=20)
    content: str | None = None
    departments: list[GreenhouseNamedNode] = Field(default_factory=list)
    offices: list[GreenhouseNamedNode] = Field(default_factory=list)
    metadata: Any = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("job title cannot be empty")
        return normalized

    @field_validator("updated_at")
    @classmethod
    def require_aware_updated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("updated_at must be timezone-aware")
        return value

    def department_names(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.name.strip() for item in self.departments))

    def office_names(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.name.strip() for item in self.offices))


class GreenhouseMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total: int | None = Field(default=None, ge=0)


class GreenhouseJobsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    jobs: list[GreenhouseJob] = Field(default_factory=list)
    meta: GreenhouseMeta | None = None

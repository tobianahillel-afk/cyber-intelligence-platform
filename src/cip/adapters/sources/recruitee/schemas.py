from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RecruiteeOffer(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | str
    slug: str = Field(min_length=1, max_length=500)
    title: str = Field(min_length=1, max_length=500)
    status: str | None = Field(default=None, max_length=50)
    department: str | None = Field(default=None, max_length=500)
    location: str | None = Field(default=None, max_length=1000)
    remote: bool | None = None
    description: str = Field(default="", max_length=500_000)
    requirements: str = Field(default="", max_length=500_000)
    created_at: datetime | None = None
    published_at: datetime | None = None
    employment_type_code: str | None = Field(default=None, max_length=100)

    @field_validator("slug", "title")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("required Recruitee text cannot be empty")
        return normalized

    @field_validator("created_at", "published_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Recruitee timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def require_publication_timestamp(self) -> RecruiteeOffer:
        if self.published_at is None and self.created_at is None:
            raise ValueError("Recruitee offer requires published_at or created_at")
        return self

    @property
    def source_job_id(self) -> str:
        return str(self.id)

    @property
    def effective_published_at(self) -> datetime:
        value = self.published_at or self.created_at
        if value is None:  # pragma: no cover - guarded by model validator
            raise ValueError("publication timestamp missing")
        return value

    def display_location(self) -> str:
        location = self.location.strip() if self.location else ""
        if self.remote is True and location:
            return f"Remote — {location}"
        if self.remote is True:
            return "Remote"
        return location or "Unspecified"


class RecruiteeOffersResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    offers: list[RecruiteeOffer] = Field(default_factory=list, max_length=10_000)

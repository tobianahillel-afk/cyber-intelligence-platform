from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RecruiteeDepartment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | str | None = None
    name: str = Field(min_length=1, max_length=500)


class RecruiteeLocation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | str | None = None
    city: str | None = Field(default=None, max_length=300)
    country_code: str | None = Field(default=None, max_length=3)
    full_address: str | None = Field(default=None, max_length=1000)

    def display_name(self) -> str | None:
        if self.full_address and self.full_address.strip():
            return self.full_address.strip()
        if self.city and self.city.strip():
            return self.city.strip()
        return None


class RecruiteeOffer(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | str
    slug: str = Field(min_length=1, max_length=500)
    title: str = Field(min_length=1, max_length=500)
    status: str | None = Field(default=None, max_length=50)
    department: RecruiteeDepartment | str | None = None
    locations: list[RecruiteeLocation] = Field(default_factory=list, max_length=100)
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

    @field_validator("created_at", "published_at", mode="before")
    @classmethod
    def normalize_provider_timestamp(cls, value: object) -> object:
        if isinstance(value, str) and value.endswith(" UTC"):
            return value.removesuffix(" UTC") + "+00:00"
        return value

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

    def department_name(self) -> str | None:
        if isinstance(self.department, RecruiteeDepartment):
            return self.department.name
        if isinstance(self.department, str) and self.department.strip():
            return self.department.strip()
        return None

    def display_location(self) -> str:
        structured = tuple(
            value
            for location in self.locations
            if (value := location.display_name()) is not None
        )
        fallback = self.location.strip() if self.location else ""
        locations = list(dict.fromkeys(structured or ((fallback,) if fallback else ())))
        rendered = "; ".join(locations)
        if self.remote is True and rendered:
            return f"Remote — {rendered}"
        if self.remote is True:
            return "Remote"
        return rendered or "Unspecified"


class RecruiteeOffersResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    offers: list[RecruiteeOffer] = Field(default_factory=list, max_length=10_000)

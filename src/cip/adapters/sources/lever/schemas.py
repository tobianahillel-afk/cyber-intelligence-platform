from __future__ import annotations

from datetime import UTC, datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, RootModel, field_validator


class LeverCategories(BaseModel):
    model_config = ConfigDict(extra="ignore")

    location: str | None = Field(default=None, max_length=500)
    commitment: str | None = Field(default=None, max_length=200)
    team: str | None = Field(default=None, max_length=300)
    department: str | None = Field(default=None, max_length=300)
    all_locations: list[str] = Field(default_factory=list, alias="allLocations")

    def normalized_location(self) -> str:
        values = [item.strip() for item in self.all_locations if item.strip()]
        if values:
            return ", ".join(dict.fromkeys(values))
        if self.location and self.location.strip():
            return self.location.strip()
        return "Unspecified"


class LeverPosting(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=500)
    categories: LeverCategories = Field(default_factory=LeverCategories)
    created_at_ms: int = Field(alias="createdAt", ge=0)
    description_plain: str | None = Field(default=None, alias="descriptionPlain")
    additional_plain: str | None = Field(default=None, alias="additionalPlain")
    hosted_url: AnyHttpUrl = Field(alias="hostedUrl")
    workplace_type: str | None = Field(default=None, alias="workplaceType", max_length=100)

    @field_validator("id", "text")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("required Lever text cannot be empty")
        return normalized

    @property
    def published_at(self) -> datetime:
        return datetime.fromtimestamp(self.created_at_ms / 1000, tz=UTC)

    def description_text(self) -> str:
        parts = (
            self.description_plain or "",
            self.additional_plain or "",
        )
        return "\n\n".join(part.strip() for part in parts if part.strip())


class LeverPostingsResponse(RootModel[list[LeverPosting]]):
    pass

from __future__ import annotations

from enum import StrEnum

from pydantic import AnyHttpUrl, BaseModel, Field, model_validator


class SourceStatus(StrEnum):
    ALLOWED = "allowed"
    CONDITIONAL = "conditional"
    BLOCKED = "blocked"


class SourceType(StrEnum):
    API = "api"
    FEED = "feed"
    WEBSITE = "website"
    MANUAL = "manual"
    LICENSED_DATASET = "licensed_dataset"


class SourcePolicy(BaseModel):
    """Machine-readable review record for one external data source."""

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{2,63}$")
    name: str = Field(min_length=1, max_length=200)
    base_url: AnyHttpUrl
    status: SourceStatus
    source_type: SourceType
    owner: str = Field(min_length=1, max_length=200)
    terms_url: AnyHttpUrl | None = None
    licence: str | None = Field(default=None, max_length=200)
    allowed_data_categories: set[str] = Field(default_factory=set)
    prohibited_data_categories: set[str] = Field(default_factory=set)
    rate_limit_per_minute: int | None = Field(default=None, ge=1)
    retention_days: int | None = Field(default=None, ge=1)
    attribution_required: bool = False
    raw_content_storage: bool = False
    human_review_required: bool = True
    notes: str = Field(default="", max_length=4_000)

    @model_validator(mode="after")
    def validate_policy(self) -> SourcePolicy:
        overlap = self.allowed_data_categories & self.prohibited_data_categories
        if overlap:
            names = ", ".join(sorted(overlap))
            raise ValueError(f"data categories cannot be both allowed and prohibited: {names}")

        if self.status is SourceStatus.BLOCKED and self.allowed_data_categories:
            raise ValueError("blocked sources cannot declare allowed data categories")

        if self.source_type is not SourceType.MANUAL and self.status is not SourceStatus.BLOCKED:
            if self.terms_url is None and self.licence is None:
                raise ValueError("automated sources require a terms URL or a documented licence")

        return self

    def permits(self, data_category: str, *, automated: bool = True) -> bool:
        if self.status is SourceStatus.BLOCKED:
            return False
        if data_category in self.prohibited_data_categories:
            return False
        if data_category not in self.allowed_data_categories:
            return False
        if automated and self.source_type is SourceType.MANUAL:
            return False
        return True

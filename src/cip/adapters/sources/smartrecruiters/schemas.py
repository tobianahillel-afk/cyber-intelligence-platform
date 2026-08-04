from __future__ import annotations

from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class SmartRecruitersLabel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str = Field(min_length=1, max_length=500)


class SmartRecruitersLocation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    city: str | None = Field(default=None, max_length=300)
    region: str | None = Field(default=None, max_length=300)
    country: str | None = Field(default=None, max_length=10)
    remote: bool = False

    def display_name(self) -> str:
        parts = [value.strip() for value in (self.city, self.region, self.country) if value]
        location = ", ".join(dict.fromkeys(part for part in parts if part))
        if self.remote and location:
            return f"Remote — {location}"
        if self.remote:
            return "Remote"
        return location or "Unspecified"


class SmartRecruitersPostingSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, max_length=200)
    uuid: str | None = Field(default=None, max_length=200)
    name: str = Field(min_length=1, max_length=500)
    released_date: datetime = Field(alias="releasedDate")
    location: SmartRecruitersLocation = Field(default_factory=SmartRecruitersLocation)
    department: SmartRecruitersLabel | None = None
    type_of_employment: SmartRecruitersLabel | None = Field(
        default=None,
        alias="typeOfEmployment",
    )
    experience_level: SmartRecruitersLabel | None = Field(
        default=None,
        alias="experienceLevel",
    )
    ref: AnyHttpUrl

    @field_validator("id", "name")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("required SmartRecruiters text cannot be empty")
        return normalized

    @field_validator("released_date")
    @classmethod
    def require_aware_released_date(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("releasedDate must be timezone-aware")
        return value


class SmartRecruitersPostingList(BaseModel):
    model_config = ConfigDict(extra="ignore")

    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    total_found: int = Field(alias="totalFound", ge=0)
    content: list[SmartRecruitersPostingSummary] = Field(default_factory=list)


class SmartRecruitersSection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str | None = None


class SmartRecruitersSections(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company_description: SmartRecruitersSection | None = Field(
        default=None,
        alias="companyDescription",
    )
    job_description: SmartRecruitersSection | None = Field(
        default=None,
        alias="jobDescription",
    )
    qualifications: SmartRecruitersSection | None = None
    additional_information: SmartRecruitersSection | None = Field(
        default=None,
        alias="additionalInformation",
    )

    def html_parts(self) -> tuple[str, ...]:
        sections = (
            self.job_description,
            self.qualifications,
            self.additional_information,
        )
        return tuple(section.text for section in sections if section and section.text)


class SmartRecruitersJobAd(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sections: SmartRecruitersSections = Field(default_factory=SmartRecruitersSections)


class SmartRecruitersPostingDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=500)
    released_date: datetime = Field(alias="releasedDate")
    location: SmartRecruitersLocation = Field(default_factory=SmartRecruitersLocation)
    department: SmartRecruitersLabel | None = None
    type_of_employment: SmartRecruitersLabel | None = Field(
        default=None,
        alias="typeOfEmployment",
    )
    experience_level: SmartRecruitersLabel | None = Field(
        default=None,
        alias="experienceLevel",
    )
    posting_url: AnyHttpUrl | None = Field(default=None, alias="postingUrl")
    job_ad: SmartRecruitersJobAd = Field(default_factory=SmartRecruitersJobAd, alias="jobAd")

    @field_validator("id", "name")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("required SmartRecruiters text cannot be empty")
        return normalized

    @field_validator("released_date")
    @classmethod
    def require_aware_released_date(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("releasedDate must be timezone-aware")
        return value

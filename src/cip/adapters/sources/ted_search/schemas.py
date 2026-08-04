from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TedNotice(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    publication_number: str = Field(alias="publication-number", min_length=1, max_length=64)
    notice_title: object = Field(alias="notice-title")
    buyer_name: object = Field(alias="buyer-name")
    buyer_country: object | None = Field(default=None, alias="buyer-country")
    publication_date: date | datetime | str | None = Field(
        default=None,
        alias="publication-date",
    )
    deadline: object | None = Field(
        default=None,
        alias="deadline-receipt-tender-date-lot",
    )
    classification_cpv: list[str] = Field(
        default_factory=list,
        alias="classification-cpv",
    )
    notice_type: object | None = Field(default=None, alias="notice-type")

    @field_validator("notice_title", "buyer_name")
    @classmethod
    def require_textual_value(cls, value: object) -> object:
        if not _flatten_text(value):
            raise ValueError("localized field must contain text")
        return value

    def title(self) -> str:
        return _first_text(self.notice_title)

    def buyer(self) -> str:
        return _first_text(self.buyer_name)

    def country(self) -> str | None:
        values = _flatten_text(self.buyer_country)
        if not values:
            return None
        country = values[0].upper()
        return country if len(country) == 3 else None

    def publication_timestamp(self) -> datetime | None:
        return _parse_datetime(self.publication_date)

    def deadline_timestamp(self) -> datetime | None:
        candidates = (_parse_datetime(value) for value in _flatten_text(self.deadline))
        return next((value for value in candidates if value is not None), None)


class TedSearchResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    notices: list[TedNotice] = Field(default_factory=list)
    iteration_next_token: str | None = Field(default=None, alias="iterationNextToken")
    total_notice_count: int | None = Field(default=None, alias="totalNoticeCount", ge=0)


def _first_text(value: object) -> str:
    values = _flatten_text(value)
    if not values:
        raise ValueError("localized field contains no text")
    return values[0]


def _flatten_text(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_flatten_text(item))
        return result
    if isinstance(value, dict):
        preferred = ("eng", "en", "fra", "fr")
        result: list[str] = []
        for key in preferred:
            if key in value:
                result.extend(_flatten_text(value[key]))
        for key, item in value.items():
            if key not in preferred:
                result.extend(_flatten_text(item))
        return result
    return []


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if not isinstance(value, str):
        return None
    normalized = value.strip().replace("Z", "+00:00")
    if not normalized:
        return None
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        try:
            return datetime.strptime(normalized, "%Y%m%d")
        except ValueError:
            return None

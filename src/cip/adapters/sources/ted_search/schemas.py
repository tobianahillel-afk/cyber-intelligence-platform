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
    procedure_identifier: object | None = Field(
        default=None,
        alias="procedure-identifier",
    )
    contract_identifier: object | None = Field(
        default=None,
        alias="contract-identifier",
    )
    contract_conclusion_date: object | None = Field(
        default=None,
        alias="contract-conclusion-date",
    )
    winner_decision_date: object | None = Field(
        default=None,
        alias="winner-decision-date",
    )
    winner_name: object | None = Field(default=None, alias="winner-name")
    winner_identifier: object | None = Field(default=None, alias="winner-identifier")
    contract_title: object | None = Field(default=None, alias="contract-title")
    tender_value: object | None = Field(default=None, alias="tender-value")
    tender_value_currency: object | None = Field(default=None, alias="tender-value-cur")

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

    def procedure_id(self) -> str | None:
        return _optional_first_text(self.procedure_identifier)

    def contract_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(_flatten_text(self.contract_identifier)))

    def notice_types(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(_flatten_text(self.notice_type)))

    def winner_names(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(_flatten_text(self.winner_name)))

    def winner_identifiers(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(_flatten_text(self.winner_identifier)))

    def contract_name(self) -> str | None:
        return _optional_first_text(self.contract_title)

    def tender_values(self) -> tuple[str, ...]:
        return tuple(_flatten_text(self.tender_value))

    def tender_currencies(self) -> tuple[str, ...]:
        return tuple(value.upper() for value in _flatten_text(self.tender_value_currency))

    def publication_timestamp(self) -> datetime | None:
        return _parse_datetime(self.publication_date)

    def deadline_timestamp(self) -> datetime | None:
        return _first_datetime(self.deadline)

    def conclusion_timestamp(self) -> datetime | None:
        return _first_datetime(self.contract_conclusion_date)

    def award_timestamp(self) -> datetime | None:
        return _first_datetime(self.winner_decision_date)


class TedSearchResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    notices: list[TedNotice] = Field(default_factory=list)
    iteration_next_token: str | None = Field(default=None, alias="iterationNextToken")
    total_notice_count: int | None = Field(default=None, alias="totalNoticeCount", ge=0)


def _first_text(value: object) -> str:
    result = _optional_first_text(value)
    if result is None:
        raise ValueError("localized field contains no text")
    return result


def _optional_first_text(value: object) -> str | None:
    values = _flatten_text(value)
    return values[0] if values else None


def _flatten_text(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, int | float):
        return [str(value)]
    if isinstance(value, list):
        list_values: list[str] = []
        for item in value:
            list_values.extend(_flatten_text(item))
        return list_values
    if isinstance(value, dict):
        preferred = ("eng", "en", "fra", "fr")
        localized_values: list[str] = []
        for key in preferred:
            if key in value:
                localized_values.extend(_flatten_text(value[key]))
        for key, item in value.items():
            if key not in preferred:
                localized_values.extend(_flatten_text(item))
        return localized_values
    return []


def _first_datetime(value: object) -> datetime | None:
    candidates = (_parse_datetime(item) for item in _flatten_text(value))
    return next((candidate for candidate in candidates if candidate is not None), None)


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

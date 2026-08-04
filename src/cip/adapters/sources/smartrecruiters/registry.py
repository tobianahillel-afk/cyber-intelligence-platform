from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

_COMPANY_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True, slots=True)
class SmartRecruitersCompany:
    id: str
    company_identifier: str
    canonical_name: str
    country_code: str | None = None
    enabled: bool = True

    def __post_init__(self) -> None:
        for field_name in ("id", "company_identifier", "canonical_name"):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} is required")
            object.__setattr__(self, field_name, value)
        if not _COMPANY_IDENTIFIER_PATTERN.fullmatch(self.company_identifier):
            raise ValueError("company_identifier contains unsupported characters")
        if self.country_code is not None:
            country = self.country_code.strip().upper()
            if len(country) != 2 or not country.isalpha():
                raise ValueError("country_code must be an ISO alpha-2 code")
            object.__setattr__(self, "country_code", country)


def load_smartrecruiters_companies(path: Path) -> tuple[SmartRecruitersCompany, ...]:
    payload = _load_yaml_mapping(path)
    if _positive_int(payload, "version") != 1:
        raise ValueError("unsupported SmartRecruiters company registry version")
    raw_companies = payload.get("companies")
    if not isinstance(raw_companies, list):
        raise ValueError("companies must be a list")
    companies: list[SmartRecruitersCompany] = []
    identities: set[str] = set()
    identifiers: set[str] = set()
    for raw in raw_companies:
        if not isinstance(raw, dict):
            raise ValueError("each SmartRecruiters company must be a mapping")
        company = _parse_company(raw)
        if company.id in identities:
            raise ValueError(f"duplicate SmartRecruiters company id: {company.id}")
        if company.company_identifier in identifiers:
            raise ValueError(
                "duplicate SmartRecruiters company identifier: "
                f"{company.company_identifier}"
            )
        identities.add(company.id)
        identifiers.add(company.company_identifier)
        companies.append(company)
    return tuple(companies)


def _parse_company(payload: dict[str, Any]) -> SmartRecruitersCompany:
    country = payload.get("country_code")
    if country is not None and not isinstance(country, str):
        raise ValueError("country_code must be a string or null")
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean")
    return SmartRecruitersCompany(
        id=_required_string(payload, "id"),
        company_identifier=_required_string(payload, "company_identifier"),
        canonical_name=_required_string(payload, "canonical_name"),
        country_code=country,
        enabled=enabled,
    )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("SmartRecruiters company registry root must be a mapping")
    return loaded


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _positive_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{key} must be a positive integer")
    return value

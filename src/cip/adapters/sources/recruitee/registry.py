from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml


@dataclass(frozen=True, slots=True)
class RecruiteeCareerSite:
    id: str
    subdomain: str
    canonical_name: str
    country_code: str | None = None
    enabled: bool = True

    def __post_init__(self) -> None:
        for field_name in ("id", "subdomain", "canonical_name"):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} is required")
            object.__setattr__(self, field_name, value)
        if not self.subdomain.replace("-", "").isalnum():
            raise ValueError("subdomain contains unsupported characters")
        if self.country_code is not None:
            country = self.country_code.strip().upper()
            if len(country) != 2 or not country.isalpha():
                raise ValueError("country_code must be an ISO alpha-2 code")
            object.__setattr__(self, "country_code", country)

    @property
    def offers_url(self) -> str:
        return f"https://{self.subdomain}.recruitee.com/api/offers/"

    def job_url(self, slug: str) -> str:
        normalized = slug.strip().strip("/")
        if not normalized:
            raise ValueError("job slug is required")
        url = f"https://{self.subdomain}.recruitee.com/o/{normalized}"
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname is None:
            raise ValueError("invalid Recruitee job URL")
        return url


def load_recruitee_sites(path: Path) -> tuple[RecruiteeCareerSite, ...]:
    payload = _load_yaml_mapping(path)
    if _positive_int(payload, "version") != 1:
        raise ValueError("unsupported Recruitee site registry version")
    raw_sites = payload.get("sites")
    if not isinstance(raw_sites, list):
        raise ValueError("sites must be a list")
    sites: list[RecruiteeCareerSite] = []
    ids: set[str] = set()
    subdomains: set[str] = set()
    for raw in raw_sites:
        if not isinstance(raw, dict):
            raise ValueError("each Recruitee site must be a mapping")
        site = _parse_site(raw)
        if site.id in ids:
            raise ValueError(f"duplicate Recruitee site id: {site.id}")
        if site.subdomain.casefold() in subdomains:
            raise ValueError(f"duplicate Recruitee subdomain: {site.subdomain}")
        ids.add(site.id)
        subdomains.add(site.subdomain.casefold())
        sites.append(site)
    return tuple(sites)


def _parse_site(payload: dict[str, Any]) -> RecruiteeCareerSite:
    country = payload.get("country_code")
    if country is not None and not isinstance(country, str):
        raise ValueError("country_code must be a string or null")
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean")
    return RecruiteeCareerSite(
        id=_required_string(payload, "id"),
        subdomain=_required_string(payload, "subdomain").lower(),
        canonical_name=_required_string(payload, "canonical_name"),
        country_code=country,
        enabled=enabled,
    )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("Recruitee site registry root must be a mapping")
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

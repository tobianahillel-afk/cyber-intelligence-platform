from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_SITE_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True, slots=True)
class LeverSite:
    id: str
    site_token: str
    canonical_name: str
    country_code: str | None = None
    enabled: bool = True

    def __post_init__(self) -> None:
        for field_name in ("id", "site_token", "canonical_name"):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} is required")
            object.__setattr__(self, field_name, value)
        if not _SITE_TOKEN_PATTERN.fullmatch(self.site_token):
            raise ValueError("site_token contains unsupported characters")
        if self.country_code is not None:
            country = self.country_code.strip().upper()
            if len(country) != 2 or not country.isalpha():
                raise ValueError("country_code must be an ISO alpha-2 code")
            object.__setattr__(self, "country_code", country)


def load_lever_sites(path: Path) -> tuple[LeverSite, ...]:
    payload = _load_yaml_mapping(path)
    if _positive_int(payload, "version") != 1:
        raise ValueError("unsupported Lever site registry version")
    raw_sites = payload.get("sites")
    if not isinstance(raw_sites, list):
        raise ValueError("sites must be a list")
    sites: list[LeverSite] = []
    identities: set[str] = set()
    tokens: set[str] = set()
    for raw in raw_sites:
        if not isinstance(raw, dict):
            raise ValueError("each Lever site must be a mapping")
        site = _parse_site(raw)
        if site.id in identities:
            raise ValueError(f"duplicate Lever site id: {site.id}")
        if site.site_token in tokens:
            raise ValueError(f"duplicate Lever site token: {site.site_token}")
        identities.add(site.id)
        tokens.add(site.site_token)
        sites.append(site)
    return tuple(sites)


def _parse_site(payload: dict[str, Any]) -> LeverSite:
    country = payload.get("country_code")
    if country is not None and not isinstance(country, str):
        raise ValueError("country_code must be a string or null")
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean")
    return LeverSite(
        id=_required_string(payload, "id"),
        site_token=_required_string(payload, "site_token"),
        canonical_name=_required_string(payload, "canonical_name"),
        country_code=country,
        enabled=enabled,
    )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("Lever site registry root must be a mapping")
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

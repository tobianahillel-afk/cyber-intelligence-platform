from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

_API_VERSION_PATTERN = re.compile(r"^20\d{6}$")


@dataclass(frozen=True, slots=True)
class TeamtailorAccount:
    id: str
    canonical_name: str
    region: Literal["eu", "na", "au"] = "eu"
    api_version: str = "20240404"
    country_code: str | None = None
    enabled: bool = False

    def __post_init__(self) -> None:
        for field_name in ("id", "canonical_name", "api_version"):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} is required")
            object.__setattr__(self, field_name, value)
        if not _API_VERSION_PATTERN.fullmatch(self.api_version):
            raise ValueError("api_version must be an 8-digit Teamtailor date version")
        if self.country_code is not None:
            country = self.country_code.strip().upper()
            if len(country) != 2 or not country.isalpha():
                raise ValueError("country_code must be an ISO alpha-2 code")
            object.__setattr__(self, "country_code", country)

    @property
    def base_url(self) -> str:
        hosts = {
            "eu": "api.teamtailor.com",
            "na": "api.na.teamtailor.com",
            "au": "api.au.teamtailor.com",
        }
        return f"https://{hosts[self.region]}"

    @property
    def jobs_url(self) -> str:
        return f"{self.base_url}/v1/jobs"


def load_teamtailor_accounts(path: Path) -> tuple[TeamtailorAccount, ...]:
    payload = _load_yaml_mapping(path)
    if _positive_int(payload, "version") != 1:
        raise ValueError("unsupported Teamtailor account registry version")
    raw_accounts = payload.get("accounts")
    if not isinstance(raw_accounts, list):
        raise ValueError("accounts must be a list")
    accounts: list[TeamtailorAccount] = []
    ids: set[str] = set()
    for raw in raw_accounts:
        if not isinstance(raw, dict):
            raise ValueError("each Teamtailor account must be a mapping")
        account = _parse_account(raw)
        if account.id in ids:
            raise ValueError(f"duplicate Teamtailor account id: {account.id}")
        ids.add(account.id)
        accounts.append(account)
    if sum(account.enabled for account in accounts) > 1:
        raise ValueError("only one Teamtailor account may use the configured API token")
    return tuple(accounts)


def _parse_account(payload: dict[str, Any]) -> TeamtailorAccount:
    country = payload.get("country_code")
    if country is not None and not isinstance(country, str):
        raise ValueError("country_code must be a string or null")
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean")
    region = _required_string(payload, "region")
    if region not in {"eu", "na", "au"}:
        raise ValueError("region must be one of eu, na, au")
    return TeamtailorAccount(
        id=_required_string(payload, "id"),
        canonical_name=_required_string(payload, "canonical_name"),
        region=region,  # type: ignore[arg-type]
        api_version=_required_string(payload, "api_version"),
        country_code=country,
        enabled=enabled,
    )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("Teamtailor account registry root must be a mapping")
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

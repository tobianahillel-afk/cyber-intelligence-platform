from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from cip.shared.kernel.time import require_aware_utc


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("public web target registry root must be a mapping")
    return loaded


def required_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping")
    return value


def required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string or null")
    return optional_text(value)


def required_bool(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def optional_bool(payload: dict[str, Any], key: str, *, default: bool) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def string_tuple(
    payload: dict[str, Any],
    key: str,
    *,
    minimum: int,
) -> tuple[str, ...]:
    value = payload.get(key, [])
    if not isinstance(value, list) or len(value) < minimum:
        raise ValueError(f"{key} must contain at least {minimum} item(s)")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{key} items must be non-empty strings")
        result.append(item)
    return tuple(result)


def bounded_int(
    payload: dict[str, Any],
    key: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    value = payload.get(key)
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or not minimum <= value <= maximum
    ):
        raise ValueError(f"{key} must be between {minimum} and {maximum}")
    return value


def optional_bounded_int(
    payload: dict[str, Any],
    key: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    value = payload.get(key, default)
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or not minimum <= value <= maximum
    ):
        raise ValueError(f"{key} must be between {minimum} and {maximum}")
    return value


def positive_int(payload: dict[str, Any], key: str) -> int:
    return bounded_int(payload, key, minimum=1, maximum=2_147_483_647)


def optional_datetime(payload: dict[str, Any], key: str) -> datetime | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, datetime):
        return require_aware_utc(value, field_name=key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be an ISO datetime or null")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{key} must be an ISO datetime or null") from exc
    return require_aware_utc(parsed, field_name=key)


def optional_time(value: datetime | None, *, field_name: str) -> datetime | None:
    if value is None:
        return None
    return require_aware_utc(value, field_name=field_name)


def optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

from cip.shared.kernel.time import require_aware_utc


def require_text(value: str, field_name: str, maximum: int) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{field_name} must be between 1 and {maximum} characters")
    return normalized


def optional_text(value: str | None, field_name: str, maximum: int) -> str | None:
    if value is None:
        return None
    return require_text(value, field_name, maximum)


def confidence(value: float) -> float:
    if not 0 <= value <= 1:
        raise ValueError("confidence must be between 0 and 1")
    return value


def source_url(value: str) -> str:
    normalized = require_text(value, "source_url", 2_048)
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source_url must use http or https")
    return normalized


def optional_url(value: str | None, field_name: str = "url") -> str | None:
    if value is None:
        return None
    normalized = require_text(value, field_name, 2_048)
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field_name} must use http or https")
    return normalized


def aware_time(value: datetime, field_name: str) -> datetime:
    return require_aware_utc(value, field_name=field_name)


def optional_time(value: datetime | None, field_name: str) -> datetime | None:
    return aware_time(value, field_name) if value is not None else None


def validity(start: datetime | None, end: datetime | None) -> None:
    if start is not None and end is not None and end < start:
        raise ValueError("valid_until cannot precede valid_from")

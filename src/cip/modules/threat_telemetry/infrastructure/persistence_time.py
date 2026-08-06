from __future__ import annotations

from datetime import UTC, datetime


def normalize_optional_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def normalize_utc(value: datetime) -> datetime:
    normalized = normalize_optional_utc(value)
    if normalized is None:
        raise ValueError("required persisted timestamp cannot be null")
    return normalized

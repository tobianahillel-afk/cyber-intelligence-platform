from __future__ import annotations

from datetime import UTC, datetime


def latest_utc(first: datetime, second: datetime) -> datetime:
    return max(_coerce_utc(first), _coerce_utc(second))


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

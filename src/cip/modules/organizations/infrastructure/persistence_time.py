from __future__ import annotations

from datetime import UTC, datetime


def coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def latest_utc(first: datetime, second: datetime) -> datetime:
    return max(coerce_utc(first), coerce_utc(second))

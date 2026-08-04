from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.dialects import postgresql, sqlite

from cip.shared.persistence.types import UTCDateTime

TYPE = UTCDateTime()


def test_utc_datetime_rejects_naive_values() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        TYPE.process_bind_param(datetime(2026, 8, 4, 12, 0), sqlite.dialect())


def test_utc_datetime_normalizes_bind_values_by_dialect() -> None:
    source = datetime(2026, 8, 4, 14, 0, tzinfo=timezone(timedelta(hours=2)))

    sqlite_value = TYPE.process_bind_param(source, sqlite.dialect())
    postgres_value = TYPE.process_bind_param(source, postgresql.dialect())

    assert sqlite_value == datetime(2026, 8, 4, 12, 0)
    assert sqlite_value is not None and sqlite_value.tzinfo is None
    assert postgres_value == datetime(2026, 8, 4, 12, 0, tzinfo=UTC)


def test_utc_datetime_restores_utc_on_read() -> None:
    naive = TYPE.process_result_value(datetime(2026, 8, 4, 12, 0), sqlite.dialect())
    offset = TYPE.process_result_value(
        datetime(2026, 8, 4, 14, 0, tzinfo=timezone(timedelta(hours=2))),
        postgresql.dialect(),
    )

    assert naive == datetime(2026, 8, 4, 12, 0, tzinfo=UTC)
    assert offset == datetime(2026, 8, 4, 12, 0, tzinfo=UTC)
    assert TYPE.process_bind_param(None, sqlite.dialect()) is None
    assert TYPE.process_result_value(None, sqlite.dialect()) is None

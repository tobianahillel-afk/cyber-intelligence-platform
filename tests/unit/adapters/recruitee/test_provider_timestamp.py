from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from cip.adapters.sources.recruitee.schemas import RecruiteeOffer


def _offer(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": 123,
        "slug": "security-engineer",
        "title": "Security Engineer",
        "created_at": "2023-01-30 13:14:40 UTC",
        "published_at": "2026-06-17 19:24:23 UTC",
    }
    payload.update(changes)
    return payload


def test_recruitee_accepts_live_provider_utc_timestamp_format() -> None:
    offer = RecruiteeOffer.model_validate(_offer())

    assert offer.created_at == datetime(2023, 1, 30, 13, 14, 40, tzinfo=UTC)
    assert offer.published_at == datetime(2026, 6, 17, 19, 24, 23, tzinfo=UTC)


def test_recruitee_still_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        RecruiteeOffer.model_validate(_offer(created_at="2026-08-11T00:25:00"))

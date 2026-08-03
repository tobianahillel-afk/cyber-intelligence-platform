from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cip.modules.cyber_intelligence.domain.entities import (
    ClaimType,
    CyberEvent,
    CyberEventType,
    EventClaim,
)

NOW = datetime(2026, 8, 3, 16, 0, tzinfo=UTC)
LATER = NOW + timedelta(days=1)


def test_cyber_event_and_claim_are_linked() -> None:
    event = CyberEvent(
        event_type=CyberEventType.DATA_BREACH,
        canonical_title="Example incident",
        first_seen_at=NOW,
        occurred_at=NOW - timedelta(hours=2),
        last_updated_at=LATER,
        confidence=0.8,
    )
    claim = EventClaim(
        event_id=event.id,
        claim_type=ClaimType.OFFICIAL_STATEMENT,
        claimant_name="Example SA",
        statement_summary="The organization confirmed an incident.",
        evidence_id=uuid4(),
        observed_at=NOW,
    )

    assert claim.event_id == event.id


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"canonical_title": ""}, "canonical_title"),
        ({"canonical_title": "x" * 501}, "500"),
        ({"confidence": 2.0}, "between 0 and 1"),
        ({"first_seen_at": datetime(2026, 8, 3)}, "timezone-aware"),
        ({"last_updated_at": NOW - timedelta(seconds=1)}, "cannot precede"),
    ],
)
def test_cyber_event_rejects_invalid_values(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "event_type": CyberEventType.SERVICE_DISRUPTION,
        "canonical_title": "Incident",
        "first_seen_at": NOW,
        "last_updated_at": NOW,
        "confidence": 0.5,
    }
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        CyberEvent(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"claimant_name": ""}, "claimant_name"),
        ({"statement_summary": ""}, "statement_summary"),
        ({"statement_summary": "x" * 4_001}, "4000"),
        ({"observed_at": datetime(2026, 8, 3)}, "timezone-aware"),
    ],
)
def test_event_claim_rejects_invalid_values(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "event_id": uuid4(),
        "claim_type": ClaimType.MEDIA_REPORT,
        "claimant_name": "Publisher",
        "statement_summary": "Report",
        "evidence_id": uuid4(),
        "observed_at": NOW,
    }
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        EventClaim(**values)  # type: ignore[arg-type]

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import DataCategory

NOW = datetime(2026, 8, 3, 16, 0, tzinfo=UTC)
LATER = NOW + timedelta(days=1)


def valid_observation(**changes: object) -> RawObservation:
    values: dict[str, object] = {
        "source_id": "source",
        "adapter_id": "source-api",
        "adapter_version": "1",
        "collection_job_id": uuid4(),
        "source_record_type": "incident",
        "source_url": "https://example.org/incidents/1",
        "payload_hash_sha256": "b" * 64,
        "data_categories": frozenset({DataCategory.PUBLIC_INCIDENT_METADATA}),
        "source_record_key": "incident-1",
        "collected_at": NOW,
        "observed_at": NOW,
        "published_at": NOW,
        "source_updated_at": NOW,
        "retention_until": LATER,
    }
    values.update(changes)
    return RawObservation(**values)  # type: ignore[arg-type]


def test_observation_builds_stable_deduplication_key() -> None:
    observation = valid_observation()

    assert observation.deduplication_key == f"source:incident-1:{'b' * 64}"


def test_observation_uses_empty_record_key_when_missing() -> None:
    observation = valid_observation(source_record_key=None)

    assert observation.deduplication_key == f"source::{'b' * 64}"


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"source_id": ""}, "source_id"),
        ({"adapter_id": ""}, "adapter_id"),
        ({"adapter_version": ""}, "adapter_version"),
        ({"source_record_type": ""}, "source_record_type"),
        ({"source_url": "mailto:test@example.org"}, "source_url"),
        ({"payload_hash_sha256": "invalid"}, "SHA-256"),
        ({"data_categories": frozenset()}, "data category"),
        ({"collected_at": datetime(2026, 8, 3)}, "timezone-aware"),
        ({"retention_until": NOW}, "later than collected_at"),
    ],
)
def test_observation_rejects_invalid_values(changes: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        valid_observation(**changes)

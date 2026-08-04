from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from textwrap import dedent

import pytest

from cip.modules.collection_orchestration.domain.models import (
    CollectionCheckpoint,
    CollectionJob,
    JobStatus,
    RetryPolicy,
    SourceSchedule,
)
from cip.modules.collection_orchestration.infrastructure.schedule_loader import (
    load_collection_schedules,
)

NOW = datetime(2026, 8, 3, 18, 26, 32, tzinfo=UTC)


def test_retry_policy_validates_and_caps_exponential_backoff() -> None:
    policy = RetryPolicy(
        max_attempts=4,
        base_delay_seconds=10,
        max_delay_seconds=25,
        circuit_failure_threshold=2,
        circuit_reset_seconds=60,
    )

    assert policy.delay_for_attempt(1) == timedelta(seconds=10)
    assert policy.delay_for_attempt(2) == timedelta(seconds=20)
    assert policy.delay_for_attempt(3) == timedelta(seconds=25)

    with pytest.raises(ValueError, match="attempt"):
        policy.delay_for_attempt(0)
    with pytest.raises(ValueError, match="max_delay_seconds"):
        RetryPolicy(base_delay_seconds=10, max_delay_seconds=9)
    with pytest.raises(ValueError, match="max_attempts"):
        RetryPolicy(max_attempts=0)
    with pytest.raises(ValueError, match="circuit_failure_threshold"):
        RetryPolicy(circuit_failure_threshold=0)
    with pytest.raises(ValueError, match="circuit_reset_seconds"):
        RetryPolicy(circuit_reset_seconds=0)


def test_schedule_builds_stable_utc_slot_and_job_key() -> None:
    schedule = SourceSchedule(
        source_id="cisa-kev",
        adapter_id="cisa-kev-feed",
        interval_seconds=900,
        lease_seconds=120,
    )
    slot = schedule.slot_for(NOW)
    first = CollectionJob.from_schedule(schedule, scheduled_for=slot)
    second = CollectionJob.from_schedule(schedule, scheduled_for=slot)

    assert slot == datetime(2026, 8, 3, 18, 15, tzinfo=UTC)
    assert first.id != second.id
    assert first.idempotency_key == second.idempotency_key
    assert first.lease_seconds == 120
    assert JobStatus.SUCCEEDED.is_terminal is True
    assert JobStatus.RUNNING.is_terminal is False


def test_schedule_and_job_reject_invalid_values() -> None:
    with pytest.raises(ValueError, match="source_id"):
        SourceSchedule("", "adapter", 10)
    with pytest.raises(ValueError, match="adapter_id"):
        SourceSchedule("source", "", 10)
    with pytest.raises(ValueError, match="interval_seconds"):
        SourceSchedule("source", "adapter", 0)
    with pytest.raises(ValueError, match="lease_seconds"):
        SourceSchedule("source", "adapter", 10, lease_seconds=0)
    with pytest.raises(ValueError, match="timezone-aware"):
        SourceSchedule("source", "adapter", 10).slot_for(datetime(2026, 8, 3))


def test_checkpoint_is_immutable_and_requires_aware_dates() -> None:
    checkpoint = CollectionCheckpoint(
        source_id="cisa-kev",
        adapter_id="cisa-kev-feed",
        payload={"etag": "abc"},
        version=1,
        updated_at=NOW,
        last_success_at=NOW,
    )

    assert checkpoint.payload["etag"] == "abc"
    with pytest.raises(TypeError):
        checkpoint.payload["etag"] = "changed"  # type: ignore[index]
    with pytest.raises(ValueError, match="version"):
        CollectionCheckpoint("source", "adapter", {}, 0, NOW)
    with pytest.raises(ValueError, match="timezone-aware"):
        CollectionCheckpoint("source", "adapter", {}, 1, datetime(2026, 8, 3))


def test_repository_collection_schedule_loads() -> None:
    schedules = load_collection_schedules(Path("policies/collection_schedules.yml"))
    schedules_by_identity = {
        (schedule.source_id, schedule.adapter_id): schedule for schedule in schedules
    }

    assert set(schedules_by_identity) == {
        ("boamp", "boamp-explore-api"),
        ("cisa-kev", "cisa-kev-feed"),
        ("ted-search", "ted-search-api"),
    }
    cisa = schedules_by_identity[("cisa-kev", "cisa-kev-feed")]
    ted = schedules_by_identity[("ted-search", "ted-search-api")]
    boamp = schedules_by_identity[("boamp", "boamp-explore-api")]
    assert cisa.interval_seconds == 900
    assert cisa.retry_policy.max_attempts == 4
    assert ted.interval_seconds == 1800
    assert ted.retry_policy.base_delay_seconds == 60
    assert boamp.interval_seconds == 1800
    assert boamp.retry_policy.max_delay_seconds == 1800


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("- invalid\n", "root must be a mapping"),
        ("version: 2\nschedules: []\n", "unsupported"),
        ("version: 1\nschedules: {}\n", "schedules must be a list"),
        ("version: 1\nschedules: [invalid]\n", "each schedule must be a mapping"),
    ],
)
def test_invalid_schedule_structure_is_rejected(
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    path = tmp_path / "schedules.yml"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_collection_schedules(path)


def test_duplicate_and_invalid_schedule_fields_are_rejected(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.yml"
    duplicate.write_text(
        dedent(
            """
            version: 1
            schedules:
              - &schedule
                source_id: cisa-kev
                adapter_id: cisa-kev-feed
                enabled: true
                interval_seconds: 900
                lease_seconds: 120
                retry:
                  max_attempts: 4
                  base_delay_seconds: 30
                  max_delay_seconds: 900
                  circuit_failure_threshold: 3
                  circuit_reset_seconds: 900
              - *schedule
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_collection_schedules(duplicate)

    invalid = tmp_path / "invalid.yml"
    invalid.write_text(
        dedent(
            """
            version: 1
            schedules:
              - source_id: cisa-kev
                adapter_id: cisa-kev-feed
                enabled: 1
                interval_seconds: 900
                lease_seconds: 120
                retry:
                  max_attempts: 4
                  base_delay_seconds: 30
                  max_delay_seconds: 900
                  circuit_failure_threshold: 3
                  circuit_reset_seconds: 900
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="enabled must be a boolean"):
        load_collection_schedules(invalid)


def test_missing_schedule_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_collection_schedules(tmp_path / "missing.yml")

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from cip.adapters.sources.greenhouse.client import GreenhouseFetchResult
from cip.adapters.sources.greenhouse.collector import (
    GreenhouseCheckpoint,
    GreenhouseCollectionDeniedError,
    GreenhouseSourceSchemaError,
    GreenhouseSourceWindowError,
    collect_greenhouse_jobs,
)
from cip.adapters.sources.greenhouse.mapper import greenhouse_job_fingerprint
from cip.adapters.sources.greenhouse.registry import GreenhouseBoard
from cip.adapters.sources.greenhouse.schemas import GreenhouseJob
from cip.modules.source_governance.domain.models import SourceStatus
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)
BOARD = GreenhouseBoard(
    id="example",
    board_token="example",
    canonical_name="Example Security",
    country_code="FR",
)


class StubGreenhouseClient:
    def __init__(self, payloads: dict[str, object]) -> None:
        self.payloads = payloads
        self.calls: list[str] = []

    def jobs_url(self, board_token: str) -> str:
        return f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"

    def fetch_jobs(self, board_token: str) -> GreenhouseFetchResult:
        self.calls.append(board_token)
        return GreenhouseFetchResult(
            body=json.dumps(self.payloads[board_token]).encode(),
            request_url=self.jobs_url(board_token),
        )


def test_collector_emits_changed_relevant_jobs_and_checkpoints_all_jobs() -> None:
    relevant = GreenhouseJob.model_validate(_job(123, "Senior SOC Analyst"))
    unchanged = GreenhouseJob.model_validate(_job(124, "SIEM Engineer"))
    non_relevant = GreenhouseJob.model_validate(_job(125, "Finance Manager"))
    previous = GreenhouseCheckpoint(
        {
            "example": {
                "124": greenhouse_job_fingerprint(unchanged),
                "125": "old-fingerprint",
            }
        }
    )
    client = StubGreenhouseClient(
        {
            "example": {
                "jobs": [
                    relevant.model_dump(mode="json"),
                    unchanged.model_dump(mode="json"),
                    non_relevant.model_dump(mode="json"),
                ],
                "meta": {"total": 3},
            }
        }
    )

    batch = collect_greenhouse_jobs(
        client,  # type: ignore[arg-type]
        _entry(),
        (BOARD,),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
        checkpoint=previous,
    )

    assert client.calls == ["example"]
    assert batch.not_modified is False
    assert set(batch.checkpoint.fingerprints["example"]) == {"123", "124", "125"}
    assert {item.source_record_key for item in batch.observations} == {
        "example:123",
    }
    assert {item.signal.title for item in batch.projections} == {
        "Senior SOC Analyst",
        "SIEM Engineer",
    }


def test_unchanged_relevant_job_refreshes_projection_without_observation() -> None:
    job = GreenhouseJob.model_validate(_job(123, "Senior SOC Analyst"))
    fingerprint = greenhouse_job_fingerprint(job)
    client = StubGreenhouseClient(
        {
            "example": {
                "jobs": [job.model_dump(mode="json")],
                "meta": {"total": 1},
            }
        }
    )

    batch = collect_greenhouse_jobs(
        client,  # type: ignore[arg-type]
        _entry(),
        (BOARD,),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
        checkpoint=GreenhouseCheckpoint({"example": {"123": fingerprint}}),
    )

    assert batch.not_modified is True
    assert batch.observations == ()
    assert len(batch.projections) == 1
    assert batch.projections[0].signal.expires_at == NOW + timedelta(days=30)


def test_removed_job_changes_checkpoint_and_stops_refreshing_projection() -> None:
    client = StubGreenhouseClient({"example": {"jobs": [], "meta": {"total": 0}}})

    batch = collect_greenhouse_jobs(
        client,  # type: ignore[arg-type]
        _entry(),
        (BOARD,),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
        checkpoint=GreenhouseCheckpoint({"example": {"123": "old"}}),
    )

    assert batch.not_modified is False
    assert batch.checkpoint.fingerprints == {"example": {}}
    assert batch.observations == ()
    assert batch.projections == ()


def test_collector_rejects_schema_drift_duplicate_ids_and_large_board() -> None:
    with pytest.raises(GreenhouseSourceSchemaError, match="schema validation"):
        collect_greenhouse_jobs(
            StubGreenhouseClient({"example": {"jobs": [{"id": 1}]}}),  # type: ignore[arg-type]
            _entry(),
            (BOARD,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )

    duplicate = _job(123, "Senior SOC Analyst")
    with pytest.raises(GreenhouseSourceSchemaError, match="duplicate job id"):
        collect_greenhouse_jobs(
            StubGreenhouseClient(  # type: ignore[arg-type]
                {"example": {"jobs": [duplicate, duplicate], "meta": {"total": 2}}}
            ),
            _entry(),
            (BOARD,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )

    with pytest.raises(GreenhouseSourceWindowError, match="job limit"):
        collect_greenhouse_jobs(
            StubGreenhouseClient(  # type: ignore[arg-type]
                {"example": {"jobs": [], "meta": {"total": 5_001}}}
            ),
            _entry(),
            (BOARD,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )


def test_collector_validates_boards_limits_and_source_policy() -> None:
    client = StubGreenhouseClient({})
    disabled = replace(BOARD, enabled=False)

    with pytest.raises(ValueError, match="at least one"):
        collect_greenhouse_jobs(
            client,  # type: ignore[arg-type]
            _entry(),
            (disabled,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )
    with pytest.raises(ValueError, match="max_jobs_per_board"):
        collect_greenhouse_jobs(
            client,  # type: ignore[arg-type]
            _entry(),
            (BOARD,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
            max_jobs_per_board=0,
        )

    entry = _entry()
    denied = replace(entry, policy=replace(entry.policy, status=SourceStatus.QUARANTINED))
    with pytest.raises(GreenhouseCollectionDeniedError, match="source_not_enabled"):
        collect_greenhouse_jobs(
            client,  # type: ignore[arg-type]
            denied,
            (BOARD,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/sources.example.yml"))
        if entry.policy.id == "greenhouse-job-board"
    )


def _job(identifier: int, title: str, **changes: object) -> dict[str, object]:
    content = (
        "<p>Join security operations and operate Microsoft Sentinel.</p>"
        if title != "Finance Manager"
        else "<p>Accounting and forecasting.</p>"
    )
    payload: dict[str, object] = {
        "id": identifier,
        "internal_job_id": identifier + 1_000,
        "title": title,
        "updated_at": "2026-08-04T10:00:00Z",
        "absolute_url": f"https://job-boards.greenhouse.io/example/jobs/{identifier}",
        "location": {"name": "Remote"},
        "language": "en",
        "content": content,
        "departments": [{"id": 1, "name": "Security"}],
        "offices": [{"id": 1, "name": "Remote"}],
        "metadata": None,
    }
    payload.update(changes)
    return payload

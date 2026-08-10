from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from textwrap import dedent
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from cip.adapters.sources.ashby.client import (
    AshbyClient,
    AshbyFetchResult,
    AshbySourceResponseError,
)
from cip.adapters.sources.ashby.collector import (
    AshbyCheckpoint,
    AshbyCollectionDeniedError,
    AshbySourceSchemaError,
    AshbySourceWindowError,
    collect_ashby_jobs,
)
from cip.adapters.sources.ashby.mapper import ashby_job_to_canonical, map_ashby_job
from cip.adapters.sources.ashby.registry import AshbyBoard, load_ashby_boards
from cip.adapters.sources.ashby.schemas import AshbyJobBoardResponse, AshbyJobPosting
from cip.modules.source_governance.domain.models import SourceStatus
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 11, 0, 20, tzinfo=UTC)
BOARD = AshbyBoard(
    id="example-security",
    board_name="ExampleSecurity",
    canonical_name="Example Security",
    country_code="FR",
)


class StubAshbyClient:
    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def board_url(self, board_name: str) -> str:
        return f"https://api.ashbyhq.com/posting-api/job-board/{board_name}"

    def fetch_jobs(self, board_name: str) -> AshbyFetchResult:
        self.calls.append(board_name)
        return AshbyFetchResult(
            body=json.dumps(self.payload).encode(),
            request_url=self.board_url(board_name),
        )


def test_repository_registry_and_schema_map_public_job() -> None:
    boards = load_ashby_boards(Path("policies/ashby_boards.yml"))
    assert boards[0].board_name == "Ashby"
    assert boards[0].enabled is True

    job = AshbyJobPosting.model_validate(_job())
    assert job.source_job_id == "job-123"
    assert job.display_location() == "Paris; Remote"
    canonical = ashby_job_to_canonical(BOARD, job)
    assert canonical.organization_key == "example-security"
    assert canonical.department == "Security"
    assert canonical.location == "Paris; Remote"

    mapped = map_ashby_job(
        BOARD,
        job,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )
    assert mapped is not None
    assert mapped[0].source_id == "ashby-job-board"
    assert mapped[0].source_record_key == "ExampleSecurity:job-123"
    assert "microsoft sentinel" in mapped[1].signal.matched_terms


def test_schema_rejects_invalid_required_fields_and_naive_time() -> None:
    with pytest.raises(ValidationError):
        AshbyJobPosting.model_validate(_job(title=" "))
    with pytest.raises(ValidationError):
        AshbyJobPosting.model_validate(_job(publishedAt="2026-08-11T00:20:00"))
    with pytest.raises(ValidationError):
        AshbyJobBoardResponse.model_validate({"apiVersion": "2", "jobs": []})


def test_client_uses_public_endpoint_and_rejects_unsafe_responses() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"apiVersion": "1", "jobs": [_job()]},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = AshbyClient(
            http_client,
            postings_base_url="https://api.ashbyhq.com/posting-api/job-board",
        )
        result = client.fetch_jobs("ExampleSecurity")
    assert "includeCompensation=false" in captured["url"]
    assert AshbyJobBoardResponse.model_validate_json(result.body).jobs

    with pytest.raises(ValueError, match="board_name"):
        client.board_url(" ")

    unsafe = httpx.MockTransport(
        lambda _: httpx.Response(200, headers={"content-type": "text/html"})
    )
    with (
        httpx.Client(transport=unsafe) as http_client,
        pytest.raises(AshbySourceResponseError, match="content type"),
    ):
        AshbyClient(http_client, postings_base_url="https://example.test").fetch_jobs(
            "Example"
        )


def test_collector_emits_changed_relevant_jobs_and_refreshes_projection() -> None:
    relevant = AshbyJobPosting.model_validate(_job())
    fingerprint = ashby_job_to_canonical(BOARD, relevant).fingerprint()
    payload = {
        "apiVersion": "1",
        "jobs": [
            relevant.model_dump(mode="json", by_alias=True),
            _job(
                jobUrl="https://jobs.ashbyhq.com/ExampleSecurity/job-finance",
                title="Finance Manager",
                department="Finance",
                descriptionPlain="Accounting and forecasting.",
            ),
            _job(
                jobUrl="https://jobs.ashbyhq.com/ExampleSecurity/job-hidden",
                isListed=False,
            ),
        ],
    }
    batch = collect_ashby_jobs(
        StubAshbyClient(payload),  # type: ignore[arg-type]
        _entry(),
        (BOARD,),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
        checkpoint=AshbyCheckpoint(
            {"example-security": {"job-123": fingerprint}}
        ),
    )
    assert batch.not_modified is False
    assert len(batch.observations) == 1
    assert batch.observations[0].source_record_key == "ExampleSecurity:job-finance"
    assert {projection.signal.title for projection in batch.projections} == {
        "Senior SOC Analyst"
    }
    assert set(batch.checkpoint.fingerprints["example-security"]) == {
        "job-123",
        "job-finance",
    }


def test_collector_rejects_governance_schema_duplicates_and_bounds() -> None:
    denied = replace(
        _entry(),
        policy=replace(_entry().policy, status=SourceStatus.QUARANTINED),
    )
    with pytest.raises(AshbyCollectionDeniedError, match="source_not_enabled"):
        _collect(StubAshbyClient({"apiVersion": "1", "jobs": []}), denied)

    with pytest.raises(AshbySourceSchemaError, match="schema validation"):
        _collect(StubAshbyClient({"apiVersion": "1", "jobs": [{"title": "bad"}]}))

    duplicate = _job()
    with pytest.raises(AshbySourceSchemaError, match="duplicate job id"):
        _collect(
            StubAshbyClient({"apiVersion": "1", "jobs": [duplicate, duplicate]})
        )

    with pytest.raises(AshbySourceWindowError, match="job limit"):
        collect_ashby_jobs(
            StubAshbyClient(
                {
                    "apiVersion": "1",
                    "jobs": [
                        _job(),
                        _job(jobUrl="https://jobs.ashbyhq.com/ExampleSecurity/job-2"),
                    ],
                }
            ),  # type: ignore[arg-type]
            _entry(),
            (BOARD,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
            max_jobs_per_board=1,
        )

    with pytest.raises(ValueError, match="at least one"):
        collect_ashby_jobs(
            StubAshbyClient({"apiVersion": "1", "jobs": []}),  # type: ignore[arg-type]
            _entry(),
            (replace(BOARD, enabled=False),),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )

    with pytest.raises(ValueError, match="max_jobs_per_board"):
        collect_ashby_jobs(
            StubAshbyClient({"apiVersion": "1", "jobs": []}),  # type: ignore[arg-type]
            _entry(),
            (BOARD,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
            max_jobs_per_board=0,
        )


def test_registry_rejects_bad_shape_duplicate_and_board_name(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.yml"
    invalid.write_text("version: 2\nboards: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        load_ashby_boards(invalid)

    duplicate = tmp_path / "duplicate.yml"
    duplicate.write_text(
        dedent(
            """
            version: 1
            boards:
              - &board
                id: example
                board_name: example
                canonical_name: Example
                country_code: FR
                enabled: true
              - *board
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate Ashby board id"):
        load_ashby_boards(duplicate)

    with pytest.raises(ValueError, match="board_name"):
        AshbyBoard(
            id="example",
            board_name="bad/name",
            canonical_name="Example",
        )


def _collect(
    client: StubAshbyClient,
    entry: SourceRegistryEntry | None = None,
) -> object:
    return collect_ashby_jobs(
        client,  # type: ignore[arg-type]
        entry or _entry(),
        (BOARD,),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/sources.ats_expansion.yml"))
        if entry.policy.id == "ashby-job-board"
    )


def _job(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "Senior SOC Analyst",
        "location": "Paris",
        "secondaryLocations": [{"location": "Remote"}, {"location": "Paris"}],
        "department": "Security",
        "team": "Detection Engineering",
        "isListed": True,
        "isRemote": True,
        "workplaceType": "Hybrid",
        "descriptionPlain": "Security operations with Microsoft Sentinel and SIEM.",
        "publishedAt": "2026-08-11T00:20:00Z",
        "employmentType": "FullTime",
        "jobUrl": "https://jobs.ashbyhq.com/ExampleSecurity/job-123",
    }
    payload.update(changes)
    return payload

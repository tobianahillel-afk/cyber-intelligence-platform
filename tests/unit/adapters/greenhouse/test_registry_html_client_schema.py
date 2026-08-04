from __future__ import annotations

from datetime import datetime
from pathlib import Path
from textwrap import dedent

import httpx
import pytest
from pydantic import ValidationError

from cip.adapters.sources.greenhouse.client import (
    GreenhouseClient,
    GreenhouseSourceResponseError,
)
from cip.adapters.sources.greenhouse.html_text import (
    MAX_NORMALIZED_TEXT_LENGTH,
    html_to_text,
)
from cip.adapters.sources.greenhouse.registry import load_greenhouse_boards
from cip.adapters.sources.greenhouse.schemas import (
    GreenhouseJob,
    GreenhouseJobsResponse,
)


def test_repository_board_registry_loads() -> None:
    boards = load_greenhouse_boards(Path("policies/greenhouse_boards.yml"))

    assert len(boards) == 1
    assert boards[0].id == "greenhouse"
    assert boards[0].board_token == "greenhouse"
    assert boards[0].canonical_name == "Greenhouse Software"
    assert boards[0].enabled is True


def test_board_registry_rejects_invalid_structures_and_duplicates(tmp_path: Path) -> None:
    invalid_cases = (
        ("- invalid\n", "root must be a mapping"),
        ("version: 2\nboards: []\n", "unsupported"),
        ("version: 1\nboards: {}\n", "boards must be a list"),
        ("version: 1\nboards: [invalid]\n", "must be a mapping"),
    )
    for index, (content, message) in enumerate(invalid_cases):
        path = tmp_path / f"invalid-{index}.yml"
        path.write_text(content, encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            load_greenhouse_boards(path)

    duplicate = tmp_path / "duplicate.yml"
    duplicate.write_text(
        dedent(
            """
            version: 1
            boards:
              - &board
                id: example
                board_token: example
                canonical_name: Example
                country_code: FR
                enabled: true
              - *board
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate Greenhouse board id"):
        load_greenhouse_boards(duplicate)


def test_board_registry_validates_fields(tmp_path: Path) -> None:
    cases = (
        ("bad/token", "board_token"),
        ("valid", "country_code"),
    )
    for index, (token, message) in enumerate(cases):
        country = "FRA" if message == "country_code" else "FR"
        path = tmp_path / f"fields-{index}.yml"
        path.write_text(
            dedent(
                f"""
                version: 1
                boards:
                  - id: example
                    board_token: {token}
                    canonical_name: Example
                    country_code: {country}
                    enabled: true
                """
            ),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match=message):
            load_greenhouse_boards(path)


def test_html_to_text_removes_markup_scripts_and_bounds_output() -> None:
    value = "<h1>SOC &amp; SIEM</h1><script>secret()</script><p>Detection&nbsp;engineering</p>"

    assert html_to_text(value) == "SOC & SIEM Detection engineering"
    assert html_to_text(None) == ""
    assert len(html_to_text("<p>" + "a" * 30_000 + "</p>")) == MAX_NORMALIZED_TEXT_LENGTH


def test_client_fetches_public_jobs_with_content() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"jobs": [], "meta": {"total": 0}},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = GreenhouseClient(
            http_client,
            boards_base_url="https://boards-api.greenhouse.io/v1/boards/",
        )
        result = client.fetch_jobs("greenhouse")

    assert client.jobs_url("greenhouse").endswith("/greenhouse/jobs")
    assert captured["url"] == (
        "https://boards-api.greenhouse.io/v1/boards/greenhouse/jobs?content=true"
    )
    assert GreenhouseJobsResponse.model_validate_json(result.body).jobs == []


def test_client_rejects_unsafe_responses() -> None:
    responses = iter(
        [
            httpx.Response(200, headers={"content-type": "text/html"}, text="no"),
            httpx.Response(
                200,
                headers={"content-type": "application/json", "content-length": "invalid"},
                content=b"{}",
            ),
            httpx.Response(
                200,
                headers={
                    "content-type": "application/json",
                    "content-length": str(GreenhouseClient.MAX_RESPONSE_BYTES + 1),
                },
                content=b"{}",
            ),
        ]
    )

    with httpx.Client(
        transport=httpx.MockTransport(lambda _: next(responses))
    ) as http_client:
        client = GreenhouseClient(http_client, boards_base_url="https://example.test")
        with pytest.raises(GreenhouseSourceResponseError, match="content type"):
            client.fetch_jobs("board")
        with pytest.raises(GreenhouseSourceResponseError, match="Content-Length"):
            client.fetch_jobs("board")
        with pytest.raises(GreenhouseSourceResponseError, match="size limit"):
            client.fetch_jobs("board")


def test_schema_normalizes_nodes_and_requires_aware_timestamp() -> None:
    job = GreenhouseJob.model_validate(_job())

    assert job.updated_at == datetime.fromisoformat("2026-08-04T10:00:00+00:00")
    assert job.department_names() == ("Security", "Engineering")
    assert job.office_names() == ("Remote",)

    with pytest.raises(ValidationError, match="timezone-aware"):
        GreenhouseJob.model_validate(_job(updated_at="2026-08-04T10:00:00"))
    with pytest.raises(ValidationError):
        GreenhouseJob.model_validate(_job(title=" "))


def _job(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": 123,
        "internal_job_id": 456,
        "title": "Senior SIEM Engineer",
        "updated_at": "2026-08-04T10:00:00Z",
        "absolute_url": "https://job-boards.greenhouse.io/example/jobs/123",
        "location": {"name": "Remote"},
        "language": "en",
        "content": "<p>Microsoft Sentinel and security operations.</p>",
        "departments": [
            {"id": 1, "name": "Security"},
            {"id": 2, "name": "Engineering"},
            {"id": 3, "name": "Security"},
        ],
        "offices": [{"id": 1, "name": "Remote"}],
        "metadata": None,
    }
    payload.update(changes)
    return payload

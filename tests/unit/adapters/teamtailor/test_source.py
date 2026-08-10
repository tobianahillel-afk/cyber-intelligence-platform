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

from cip.adapters.sources.teamtailor.client import (
    TeamtailorClient,
    TeamtailorFetchResult,
    TeamtailorSourceResponseError,
)
from cip.adapters.sources.teamtailor.collector import (
    TeamtailorCollectionDeniedError,
    TeamtailorSourceSchemaError,
    TeamtailorSourceWindowError,
    collect_teamtailor_jobs,
)
from cip.adapters.sources.teamtailor.mapper import (
    map_teamtailor_job,
    teamtailor_job_to_canonical,
)
from cip.adapters.sources.teamtailor.registry import (
    TeamtailorAccount,
    load_teamtailor_accounts,
)
from cip.adapters.sources.teamtailor.schemas import (
    TeamtailorJobResource,
    TeamtailorJobsResponse,
)
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.collection_orchestration.application.teamtailor_adapter import (
    TeamtailorAdapter,
)
from cip.modules.source_governance.domain.models import SourceStatus
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 11, 0, 30, tzinfo=UTC)
ACCOUNT = TeamtailorAccount(
    id="example-security",
    canonical_name="Example Security",
    region="eu",
    api_version="20240404",
    country_code="FR",
    enabled=True,
)


class StubTeamtailorClient:
    def __init__(self, pages: dict[str, object]) -> None:
        self.pages = pages
        self.calls: list[tuple[str, str, str]] = []

    def fetch_jobs_page(
        self,
        url: str,
        *,
        api_token: str,
        api_version: str,
        page_size: int = 30,
    ) -> TeamtailorFetchResult:
        self.calls.append((url, api_token, api_version))
        return TeamtailorFetchResult(
            body=json.dumps(self.pages[url]).encode(),
            request_url=url,
        )


def test_repository_registry_is_fail_closed_without_account() -> None:
    assert load_teamtailor_accounts(Path("policies/teamtailor_accounts.yml")) == ()
    assert ACCOUNT.base_url == "https://api.teamtailor.com"
    assert ACCOUNT.jobs_url == "https://api.teamtailor.com/v1/jobs"


def test_schema_and_mapper_use_public_job_fields_only() -> None:
    job = TeamtailorJobResource.model_validate(_job())
    canonical = teamtailor_job_to_canonical(ACCOUNT, job)
    assert canonical.department is None
    assert canonical.employment_type == "full-time"
    assert canonical.location == "hybrid"
    assert canonical.source_url == "https://api.teamtailor.com/v1/jobs/123"

    mapped = map_teamtailor_job(
        ACCOUNT,
        job,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )
    assert mapped is not None
    assert mapped[0].source_id == "teamtailor-public-jobs"
    assert "microsoft sentinel" in mapped[1].signal.matched_terms

    with pytest.raises(ValidationError):
        TeamtailorJobResource.model_validate(_job(type="candidates"))


def test_client_sends_minimal_public_read_headers_and_bounds_pages() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["authorization"]
        captured["api_version"] = request.headers["x-api-version"]
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            headers={"content-type": "application/vnd.api+json"},
            json={"data": [_job()], "links": {"next": None}},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = TeamtailorClient(http_client)
        result = client.fetch_jobs_page(
            ACCOUNT.jobs_url,
            api_token="public-read-token",
            api_version=ACCOUNT.api_version,
        )
    assert captured["authorization"] == "Token token=public-read-token"
    assert captured["api_version"] == "20240404"
    assert "page%5Bsize%5D=30" in captured["url"]
    assert TeamtailorJobsResponse.model_validate_json(result.body).data

    with pytest.raises(ValueError, match="api_token"):
        client.fetch_jobs_page(
            ACCOUNT.jobs_url,
            api_token=" ",
            api_version=ACCOUNT.api_version,
        )
    with pytest.raises(ValueError, match="page_size"):
        client.fetch_jobs_page(
            ACCOUNT.jobs_url,
            api_token="token",
            api_version=ACCOUNT.api_version,
            page_size=31,
        )


def test_client_rejects_non_json_api_response() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, headers={"content-type": "text/html"})
    )
    with (
        httpx.Client(transport=transport) as http_client,
        pytest.raises(TeamtailorSourceResponseError, match="content type"),
    ):
        TeamtailorClient(http_client).fetch_jobs_page(
            ACCOUNT.jobs_url,
            api_token="token",
            api_version=ACCOUNT.api_version,
        )


def test_collector_follows_only_same_provider_jobs_pagination() -> None:
    second = f"{ACCOUNT.jobs_url}?page%5Bnumber%5D=2"
    client = StubTeamtailorClient(
        {
            ACCOUNT.jobs_url: {
                "data": [_job()],
                "links": {"next": second},
            },
            second: {
                "data": [
                    _job(
                        id="456",
                        attributes=_attributes(
                            title="Finance Manager",
                            body="Accounting and forecasting.",
                        ),
                    )
                ],
                "links": {"next": None},
            },
        }
    )
    batch = collect_teamtailor_jobs(
        client,  # type: ignore[arg-type]
        _entry(),
        ACCOUNT,
        api_token="public-read-token",
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )
    assert len(client.calls) == 2
    assert {projection.signal.title for projection in batch.projections} == {
        "Senior SOC Analyst"
    }
    assert set(batch.checkpoint.fingerprints[ACCOUNT.id]) == {"123", "456"}

    escaped = StubTeamtailorClient(
        {
            ACCOUNT.jobs_url: {
                "data": [],
                "links": {"next": "https://example.org/v1/jobs"},
            }
        }
    )
    with pytest.raises(TeamtailorSourceSchemaError, match="outside provider host"):
        _collect(escaped)


def test_collector_rejects_governance_duplicates_loops_and_window() -> None:
    denied = replace(
        _entry(),
        policy=replace(_entry().policy, status=SourceStatus.QUARANTINED),
    )
    with pytest.raises(TeamtailorCollectionDeniedError, match="source_not_enabled"):
        _collect(
            StubTeamtailorClient(
                {ACCOUNT.jobs_url: {"data": [], "links": {"next": None}}}
            ),
            denied,
        )

    duplicate = _job()
    with pytest.raises(TeamtailorSourceSchemaError, match="duplicate job id"):
        _collect(
            StubTeamtailorClient(
                {
                    ACCOUNT.jobs_url: {
                        "data": [duplicate, duplicate],
                        "links": {"next": None},
                    }
                }
            )
        )

    with pytest.raises(TeamtailorSourceWindowError, match="job limit"):
        collect_teamtailor_jobs(
            StubTeamtailorClient(
                {
                    ACCOUNT.jobs_url: {
                        "data": [_job(), _job(id="456")],
                        "links": {"next": None},
                    }
                }
            ),  # type: ignore[arg-type]
            _entry(),
            ACCOUNT,
            api_token="token",
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
            max_jobs=1,
        )

    loop = StubTeamtailorClient(
        {
            ACCOUNT.jobs_url: {
                "data": [],
                "links": {"next": ACCOUNT.jobs_url},
            }
        }
    )
    with pytest.raises(TeamtailorSourceSchemaError, match="pagination loop"):
        _collect(loop)


def test_application_adapter_fails_closed_without_public_read_secret() -> None:
    adapter = TeamtailorAdapter(_entry(), ACCOUNT, lambda: None)
    with pytest.raises(AdapterExecutionError, match="token is unavailable") as exc:
        adapter.collect(
            collection_job_id=uuid4(),
            checkpoint_payload=None,
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )
    assert exc.value.error_code == "provider_secret_unavailable"


def test_registry_rejects_multiple_enabled_accounts(tmp_path: Path) -> None:
    path = tmp_path / "teamtailor.yml"
    path.write_text(
        dedent(
            """
            version: 1
            accounts:
              - id: one
                canonical_name: One
                region: eu
                api_version: "20240404"
                enabled: true
              - id: two
                canonical_name: Two
                region: na
                api_version: "20240404"
                enabled: true
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="only one"):
        load_teamtailor_accounts(path)


def _collect(
    client: StubTeamtailorClient,
    entry: SourceRegistryEntry | None = None,
) -> object:
    return collect_teamtailor_jobs(
        client,  # type: ignore[arg-type]
        entry or _entry(),
        ACCOUNT,
        api_token="public-read-token",
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/sources.ats_expansion.yml"))
        if entry.policy.id == "teamtailor-public-jobs"
    )


def _job(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "123",
        "type": "jobs",
        "attributes": _attributes(),
        "links": {"self": "https://api.teamtailor.com/v1/jobs/123"},
    }
    payload.update(changes)
    return payload


def _attributes(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "Senior SOC Analyst",
        "body": "<p>Operate Microsoft Sentinel and SIEM detections.</p>",
        "pitch": "Security operations",
        "remote-status": "hybrid",
        "employment-type": "full-time",
        "created-at": "2026-08-11T00:30:00Z",
    }
    payload.update(changes)
    return payload

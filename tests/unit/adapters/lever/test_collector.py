from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from cip.adapters.sources.lever.client import LeverFetchResult
from cip.adapters.sources.lever.collector import (
    LeverCheckpoint,
    LeverCollectionDeniedError,
    LeverSourceSchemaError,
    LeverSourceWindowError,
    collect_lever_jobs,
)
from cip.adapters.sources.lever.mapper import lever_posting_to_canonical
from cip.adapters.sources.lever.registry import LeverSite
from cip.adapters.sources.lever.schemas import LeverPosting
from cip.modules.source_governance.domain.models import SourceStatus
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 4, 14, 0, tzinfo=UTC)
SITE = LeverSite(
    id="example-security",
    site_token="example",
    canonical_name="Example Security",
    country_code="FR",
)


class StubLeverClient:
    def __init__(self, pages: dict[int, object]) -> None:
        self.pages = pages
        self.calls: list[tuple[str, int, int]] = []

    def postings_url(self, site_token: str) -> str:
        return f"https://api.lever.co/v0/postings/{site_token}"

    def fetch_postings(
        self,
        site_token: str,
        *,
        skip: int,
        limit: int,
    ) -> LeverFetchResult:
        self.calls.append((site_token, skip, limit))
        return LeverFetchResult(
            body=json.dumps(self.pages[skip]).encode(),
            request_url=self.postings_url(site_token),
        )


def test_collector_paginates_and_emits_only_changed_relevant_postings() -> None:
    unchanged = LeverPosting.model_validate(_posting("job-2", "SIEM Engineer"))
    previous = LeverCheckpoint(
        {
            "example-security": {
                "job-2": lever_posting_to_canonical(SITE, unchanged).fingerprint(),
                "removed": "old",
            }
        }
    )
    client = StubLeverClient(
        {
            0: [
                _posting("job-1", "Senior SOC Analyst"),
                unchanged.model_dump(mode="json", by_alias=True),
            ],
            2: [_posting("job-3", "Finance Manager")],
        }
    )

    batch = collect_lever_jobs(
        client,  # type: ignore[arg-type]
        _entry(),
        (SITE,),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
        checkpoint=previous,
        page_size=2,
    )

    assert client.calls == [("example", 0, 2), ("example", 2, 2)]
    assert batch.not_modified is False
    assert set(batch.checkpoint.fingerprints["example-security"]) == {
        "job-1",
        "job-2",
        "job-3",
    }
    assert {item.source_record_key for item in batch.observations} == {
        "example:job-1"
    }
    assert {item.signal.title for item in batch.projections} == {
        "Senior SOC Analyst",
        "SIEM Engineer",
    }


def test_unchanged_relevant_posting_refreshes_projection_without_observation() -> None:
    posting = LeverPosting.model_validate(_posting("job-1", "Senior SOC Analyst"))
    fingerprint = lever_posting_to_canonical(SITE, posting).fingerprint()
    client = StubLeverClient({0: [posting.model_dump(mode="json", by_alias=True)]})

    batch = collect_lever_jobs(
        client,  # type: ignore[arg-type]
        _entry(),
        (SITE,),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
        checkpoint=LeverCheckpoint({"example-security": {"job-1": fingerprint}}),
    )

    assert batch.not_modified is True
    assert batch.observations == ()
    assert len(batch.projections) == 1
    assert batch.projections[0].signal.expires_at == NOW + timedelta(days=30)


def test_removed_posting_changes_checkpoint_and_stops_projection_refresh() -> None:
    batch = collect_lever_jobs(
        StubLeverClient({0: []}),  # type: ignore[arg-type]
        _entry(),
        (SITE,),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
        checkpoint=LeverCheckpoint({"example-security": {"job-1": "old"}}),
    )

    assert batch.not_modified is False
    assert batch.checkpoint.fingerprints == {"example-security": {}}
    assert batch.observations == ()
    assert batch.projections == ()


def test_collector_rejects_schema_drift_duplicates_and_large_window() -> None:
    with pytest.raises(LeverSourceSchemaError, match="schema validation"):
        collect_lever_jobs(
            StubLeverClient({0: [{"id": "incomplete"}]}),  # type: ignore[arg-type]
            _entry(),
            (SITE,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )

    duplicate = _posting("job-1", "SOC Analyst")
    with pytest.raises(LeverSourceSchemaError, match="duplicate posting id"):
        collect_lever_jobs(
            StubLeverClient({0: [duplicate, duplicate]}),  # type: ignore[arg-type]
            _entry(),
            (SITE,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
            page_size=3,
        )

    with pytest.raises(LeverSourceWindowError, match="job limit"):
        collect_lever_jobs(
            StubLeverClient(
                {
                    0: [
                        _posting("job-1", "SOC Analyst"),
                        _posting("job-2", "SIEM Engineer"),
                    ]
                }
            ),  # type: ignore[arg-type]
            _entry(),
            (SITE,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
            page_size=2,
            max_jobs_per_site=1,
        )


def test_collector_validates_sites_limits_and_governance() -> None:
    client = StubLeverClient({})
    disabled = replace(SITE, enabled=False)

    with pytest.raises(ValueError, match="at least one"):
        collect_lever_jobs(
            client,  # type: ignore[arg-type]
            _entry(),
            (disabled,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )
    with pytest.raises(ValueError, match="page_size"):
        collect_lever_jobs(
            client,  # type: ignore[arg-type]
            _entry(),
            (SITE,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
            page_size=0,
        )
    with pytest.raises(ValueError, match="max_jobs_per_site"):
        collect_lever_jobs(
            client,  # type: ignore[arg-type]
            _entry(),
            (SITE,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
            max_jobs_per_site=0,
        )

    entry = _entry()
    denied = replace(entry, policy=replace(entry.policy, status=SourceStatus.QUARANTINED))
    with pytest.raises(LeverCollectionDeniedError, match="source_not_enabled"):
        collect_lever_jobs(
            client,  # type: ignore[arg-type]
            denied,
            (SITE,),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/sources.example.yml"))
        if entry.policy.id == "lever-job-board"
    )


def _posting(identifier: str, title: str) -> dict[str, object]:
    relevant = title != "Finance Manager"
    return {
        "id": identifier,
        "text": title,
        "categories": {
            "location": "Paris",
            "allLocations": ["Paris"],
            "commitment": "Full-time",
            "department": "Security" if relevant else "Finance",
        },
        "createdAt": 1_775_290_400_000,
        "descriptionPlain": (
            "Security operations and Microsoft Sentinel."
            if relevant
            else "Accounting and forecasting."
        ),
        "additionalPlain": "",
        "hostedUrl": f"https://jobs.lever.co/example/{identifier}",
        "workplaceType": "hybrid",
    }

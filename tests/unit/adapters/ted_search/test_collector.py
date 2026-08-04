from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from cip.adapters.sources.ted_search.client import (
    TedSearchCheckpoint,
    TedSearchClient,
    TedSearchFetchResult,
)
from cip.adapters.sources.ted_search.collector import (
    TedSourceSchemaError,
    collect_ted_notices,
)
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 4, 10, 0, tzinfo=UTC)


class StubTedClient(TedSearchClient):
    def __init__(self, payload: object) -> None:
        self._body = json.dumps(payload).encode()

    def fetch(self) -> TedSearchFetchResult:
        return TedSearchFetchResult(body=self._body)


def test_collector_maps_only_new_relevant_notices() -> None:
    client = StubTedClient(
        {
            "notices": [
                _notice("300-2026", "SIEM managed service"),
                _notice("200-2026", "Office furniture"),
                _notice("100-2026", "SOC monitoring platform"),
            ],
            "totalNoticeCount": 3,
        }
    )

    batch = collect_ted_notices(
        client,
        _entry(),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=730),
        checkpoint=TedSearchCheckpoint(latest_publication_number="100-2026"),
    )

    assert batch.not_modified is False
    assert batch.checkpoint.latest_publication_number == "300-2026"
    assert len(batch.observations) == 1
    assert len(batch.projections) == 1
    assert batch.projections[0].signal.title == "SIEM managed service"


def test_collector_marks_unchanged_first_page() -> None:
    batch = collect_ted_notices(
        StubTedClient({"notices": [_notice("300-2026", "SIEM managed service")]}),
        _entry(),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=730),
        checkpoint=TedSearchCheckpoint(latest_publication_number="300-2026"),
    )

    assert batch.not_modified is True
    assert batch.observations == ()
    assert batch.projections == ()


def test_collector_rejects_schema_drift() -> None:
    with pytest.raises(TedSourceSchemaError, match="schema validation"):
        collect_ted_notices(
            StubTedClient({"notices": [{"publication-number": "missing-fields"}]}),
            _entry(),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=730),
        )


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/sources.example.yml"))
        if entry.policy.id == "ted-search"
    )


def _notice(number: str, title: str) -> dict[str, object]:
    return {
        "publication-number": number,
        "notice-title": {"eng": title},
        "buyer-name": {"eng": ["Public Buyer"]},
        "buyer-country": ["FRA"],
        "publication-date": "2026-08-04",
        "deadline-receipt-tender-date-lot": ["2026-08-20T12:00:00Z"],
        "classification-cpv": ["72000000"],
        "notice-type": ["cn-standard"],
    }

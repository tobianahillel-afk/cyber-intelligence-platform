from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from cip.adapters.sources.boamp.client import BoampCheckpoint, BoampFetchResult
from cip.adapters.sources.boamp.collector import (
    BoampCollectionDeniedError,
    BoampSourceSchemaError,
    BoampSourceWindowError,
    collect_boamp_notices,
)
from cip.modules.source_governance.domain.models import SourceStatus
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 4, 10, 0, tzinfo=UTC)


class StubBoampClient:
    PAGE_SIZE = 2

    def __init__(self, pages: dict[int, object]) -> None:
        self.pages = pages
        self.calls: list[tuple[date, int]] = []

    def fetch_page(self, *, since_date: date, offset: int) -> BoampFetchResult:
        self.calls.append((since_date, offset))
        return BoampFetchResult(body=json.dumps(self.pages[offset]).encode())


def test_collector_paginates_stops_at_checkpoint_and_maps_relevant_notices() -> None:
    client = StubBoampClient(
        {
            0: {
                "total_count": 4,
                "results": [
                    _notice("26-new", "Service SIEM et SOC"),
                    _notice("26-office", "Fourniture de mobilier"),
                ],
            },
            2: {
                "total_count": 4,
                "results": [
                    _notice("26-old", "Plateforme XDR"),
                    _notice("26-older", "Service SOC"),
                ],
            },
        }
    )

    batch = collect_boamp_notices(
        client,  # type: ignore[arg-type]
        _entry(),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=730),
        checkpoint=BoampCheckpoint(
            latest_idweb="26-old",
            latest_publication_date="2026-08-03",
        ),
    )

    assert client.calls == [(date(2026, 8, 3), 0), (date(2026, 8, 3), 2)]
    assert batch.not_modified is False
    assert batch.checkpoint.latest_idweb == "26-new"
    assert batch.checkpoint.latest_publication_date == "2026-08-04"
    assert len(batch.observations) == 1
    assert len(batch.projections) == 1
    assert batch.projections[0].signal.title == "Service SIEM et SOC"


def test_collector_marks_unchanged_first_record() -> None:
    client = StubBoampClient(
        {
            0: {
                "total_count": 1,
                "results": [_notice("26-current", "Service SIEM")],
            }
        }
    )

    batch = collect_boamp_notices(
        client,  # type: ignore[arg-type]
        _entry(),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=730),
        checkpoint=BoampCheckpoint(
            latest_idweb="26-current",
            latest_publication_date="2026-08-04",
        ),
    )

    assert batch.not_modified is True
    assert batch.observations == ()
    assert batch.projections == ()


def test_collector_rejects_schema_drift_invalid_checkpoint_and_window_overflow() -> None:
    with pytest.raises(BoampSourceSchemaError, match="schema validation"):
        collect_boamp_notices(
            StubBoampClient({0: {"results": [{"idweb": "missing"}]}}),  # type: ignore[arg-type]
            _entry(),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=730),
        )

    with pytest.raises(BoampSourceSchemaError, match="checkpoint"):
        collect_boamp_notices(
            StubBoampClient({}),  # type: ignore[arg-type]
            _entry(),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=730),
            checkpoint=BoampCheckpoint(latest_publication_date="not-a-date"),
        )

    overflow = StubBoampClient(
        {
            0: {
                "total_count": 3,
                "results": [
                    _notice("26-1", "Service SIEM"),
                    _notice("26-2", "Service SOC"),
                ],
            }
        }
    )
    with pytest.raises(BoampSourceWindowError, match="pagination budget"):
        collect_boamp_notices(
            overflow,  # type: ignore[arg-type]
            _entry(),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=730),
            max_pages=1,
        )


def test_collector_rejects_denied_policy_and_invalid_page_budget() -> None:
    entry = _entry()
    denied = replace(entry, policy=replace(entry.policy, status=SourceStatus.QUARANTINED))

    with pytest.raises(BoampCollectionDeniedError, match="source_not_enabled"):
        collect_boamp_notices(
            StubBoampClient({}),  # type: ignore[arg-type]
            denied,
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=730),
        )
    with pytest.raises(ValueError, match="max_pages"):
        collect_boamp_notices(
            StubBoampClient({}),  # type: ignore[arg-type]
            entry,
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=730),
            max_pages=0,
        )


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/sources.example.yml"))
        if entry.policy.id == "boamp"
    )


def _notice(identifier: str, title: str) -> dict[str, object]:
    return {
        "idweb": identifier,
        "objet": title,
        "dateparution": "2026-08-04",
        "datelimitereponse": "2026-08-30T12:00:00Z",
        "nomacheteur": "Ville Exemple",
        "etat": "initial",
        "nature_libelle": "Avis de marché",
        "type_avis": ["Avis de marché"],
        "descripteur_libelle": [title],
        "type_marche": ["Services"],
        "url_avis": f"https://www.boamp.fr/avis/{identifier}",
    }

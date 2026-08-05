from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from cip.adapters.sources.decp.client import DecpCheckpoint, DecpFetchResult
from cip.adapters.sources.decp.collector import (
    DecpSourceSchemaError,
    DecpSourceWindowError,
    collect_decp_contracts,
)
from cip.modules.procurement_history.domain.models import ProcurementPublicationKind
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 5, 10, 0, tzinfo=UTC)


class StubDecpClient:
    PAGE_SIZE = 100

    def __init__(self, pages: list[object]) -> None:
        self._pages = [json.dumps(page).encode() for page in pages]
        self.offsets: list[int] = []

    def fetch_page(self, *, offset: int) -> DecpFetchResult:
        self.offsets.append(offset)
        return DecpFetchResult(body=self._pages[offset // self.PAGE_SIZE])


def test_collector_maps_relevant_contracts_and_checkpoint() -> None:
    client = StubDecpClient(
        [
            {
                "total_count": 2,
                "results": [
                    _record("MARCHE-002", "Audit ISO 27001 et PAM"),
                    _record("MARCHE-001", "Mobilier de bureau"),
                ],
            }
        ]
    )

    batch = collect_decp_contracts(
        client,  # type: ignore[arg-type]
        _entry(),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=3650),
    )

    assert client.offsets == [0]
    assert len(batch.observations) == 1
    assert len(batch.buyers) == 1
    assert len(batch.procurement) == 1
    assert batch.procurement[0].publication.kind is ProcurementPublicationKind.AWARD
    assert batch.checkpoint.latest_revision_key == (
        batch.procurement[0].publication.revision_key
    )
    assert batch.checkpoint.latest_publication_date == "2026-09-02"
    assert batch.not_modified is False


def test_collector_stops_at_checkpoint_without_replaying_revision() -> None:
    first = collect_decp_contracts(
        StubDecpClient(
            [
                {
                    "total_count": 1,
                    "results": [_record("MARCHE-002", "Audit ISO 27001 et PAM")],
                }
            ]
        ),  # type: ignore[arg-type]
        _entry(),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=3650),
    )
    previous = first.checkpoint.latest_revision_key
    assert previous is not None

    replay = collect_decp_contracts(
        StubDecpClient(
            [
                {
                    "total_count": 1,
                    "results": [_record("MARCHE-002", "Audit ISO 27001 et PAM")],
                }
            ]
        ),  # type: ignore[arg-type]
        _entry(),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=3650),
        checkpoint=DecpCheckpoint(
            latest_revision_key=previous,
            latest_publication_date="2026-09-02",
        ),
    )

    assert replay.not_modified is True
    assert replay.observations == ()
    assert replay.procurement == ()


def test_collector_rejects_schema_drift_and_lost_checkpoint_window() -> None:
    with pytest.raises(DecpSourceSchemaError, match="schema validation"):
        collect_decp_contracts(
            StubDecpClient([{"total_count": 1, "results": [{"id": "missing"}]}]),  # type: ignore[arg-type]
            _entry(),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=3650),
        )

    full_page = [_record(f"MARCHE-{index:03d}", "Audit cybersécurité") for index in range(100)]
    with pytest.raises(DecpSourceWindowError, match="checkpoint"):
        collect_decp_contracts(
            StubDecpClient([{"total_count": 501, "results": full_page}]),  # type: ignore[arg-type]
            _entry(),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=3650),
            checkpoint=DecpCheckpoint(latest_revision_key="missing"),
            max_pages=1,
        )


def _entry() -> SourceRegistryEntry:
    return load_source_registry(Path("policies/sources.decp.yml"))[0]


def _record(record_id: str, title: str) -> dict[str, object]:
    return {
        "id": record_id,
        "nature": "Marché",
        "objet": title,
        "codecpv": "72000000",
        "procedure": "Appel d'offres ouvert",
        "acheteur_id": "11111111111111",
        "acheteur_nom": "Métropole Exemple",
        "dureemois": 12,
        "datenotification": "2026-09-01",
        "datepublicationdonnees": "2026-09-02",
        "montant": 250000,
        "titulaire_denominationsociale_1": "Provider SAS",
        "titulaire_id_1": "22222222222222",
        "titulaire_typeidentifiant_1": "SIRET",
        "booleanmodification": False,
    }

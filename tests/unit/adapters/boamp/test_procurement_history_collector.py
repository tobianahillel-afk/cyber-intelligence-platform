from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from cip.adapters.sources.boamp.client import BoampFetchResult
from cip.adapters.sources.boamp.collector import collect_boamp_notices
from cip.modules.procurement_history.domain.models import (
    PartyResolutionStatus,
    ProcurementPublicationKind,
)
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 5, 10, 0, tzinfo=UTC)


class ResultClient:
    PAGE_SIZE = 100

    def fetch_page(self, *, since_date: date, offset: int) -> BoampFetchResult:
        assert since_date == date(2026, 8, 3)
        assert offset == 0
        payload = {
            "total_count": 1,
            "results": [
                {
                    "idweb": "26-award-001",
                    "objet": "Attribution audit ISO 27001, PAM et réponse à incident",
                    "dateparution": "2026-08-05",
                    "datelimitereponse": None,
                    "nomacheteur": "Métropole Exemple",
                    "etat": "initial",
                    "nature_libelle": "Avis de résultat",
                    "type_avis": ["Avis de résultat d'attribution"],
                    "descripteur_libelle": ["Cybersécurité"],
                    "type_marche": ["Services"],
                    "titulaire": [{"denomination": "Provider SAS"}],
                    "url_avis": "https://www.boamp.fr/avis/26-award-001",
                }
            ],
        }
        return BoampFetchResult(body=json.dumps(payload).encode())


def test_result_collector_emits_history_and_contract_without_current_signal() -> None:
    batch = collect_boamp_notices(
        ResultClient(),  # type: ignore[arg-type]
        _entry(),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=730),
    )

    assert len(batch.observations) == 1
    assert batch.projections == ()
    assert len(batch.buyers) == 1
    assert len(batch.procurement) == 1
    history = batch.procurement[0]
    assert history.publication.kind is ProcurementPublicationKind.AWARD
    assert history.publication.buyer_organization_id == batch.buyers[0].id
    assert history.contract is not None
    assert history.contract.parties[0].published_name == "Provider SAS"
    assert (
        history.contract.parties[0].resolution_status
        is PartyResolutionStatus.UNRESOLVED
    )


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/sources.example.yml"))
        if entry.policy.id == "boamp"
    )

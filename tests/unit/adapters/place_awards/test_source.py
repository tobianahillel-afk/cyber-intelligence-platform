from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from cip.adapters.sources.place_awards.client import (
    PlaceAwardsClient,
    PlaceFetchResult,
    PlaceSourceResponseError,
)
from cip.adapters.sources.place_awards.collector import (
    PlaceCheckpoint,
    PlaceCollectionDeniedError,
    PlaceSourceSchemaError,
    PlaceSourceWindowError,
    collect_place_awards,
)
from cip.adapters.sources.place_awards.mapper import map_place_award
from cip.adapters.sources.place_awards.schemas import PlaceAward, PlaceAwardsResponse
from cip.modules.procurement_history.domain.models import ProcurementPublicationKind
from cip.modules.source_governance.domain.models import SourceStatus
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 11, 8, 0, tzinfo=UTC)


class StubPlaceClient:
    PAGE_SIZE = 100

    def __init__(self, pages: list[dict[str, object]]) -> None:
        self.pages = pages
        self.offsets: list[int] = []

    def fetch_page(self, *, offset: int) -> PlaceFetchResult:
        self.offsets.append(offset)
        index = offset // self.PAGE_SIZE
        payload = self.pages[index] if index < len(self.pages) else {
            "total_count": 0,
            "results": [],
        }
        return PlaceFetchResult(json.dumps(payload).encode())


def test_schema_and_mapper_preserve_award_history_without_cyber_filter() -> None:
    award = PlaceAward.model_validate(_award(objet_du_marche="Fourniture de mobilier"))
    mapped = map_place_award(
        award,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )

    assert mapped.observation.source_id == "place-awards"
    assert mapped.observation.source_record_type == "procurement_award"
    assert mapped.procurement.publication.kind is ProcurementPublicationKind.AWARD
    assert mapped.procurement.contract is not None
    assert mapped.procurement.contract.title == "Fourniture de mobilier"
    assert mapped.procurement.contract.service_families == ()
    assert mapped.procurement.contract.parties[0].official_identifier == "SIRET:12345678901234"
    assert mapped.buyer.canonical_name == "Service des achats"


def test_schema_rejects_blank_required_and_negative_amount() -> None:
    with pytest.raises(ValidationError):
        PlaceAward.model_validate(_award(objet_du_marche=" "))
    with pytest.raises(ValidationError):
        PlaceAward.model_validate(_award(montant=-1))
    with pytest.raises(ValidationError):
        PlaceAwardsResponse.model_validate({"total_count": -1, "results": []})


def test_client_uses_selected_fields_and_bounded_offset() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"total_count": 1, "results": [_award()]},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = PlaceAwardsClient(http_client, records_url="https://example.test/records")
        response = client.fetch_page(offset=0)
    assert PlaceAwardsResponse.model_validate_json(response.body).total_count == 1
    assert "select=" in captured["url"]
    assert "limit=100" in captured["url"]

    with pytest.raises(ValueError, match="page boundary"):
        client.fetch_page(offset=1)


def test_client_rejects_non_json_and_oversized_response() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, headers={"content-type": "text/html"}, text="bad")
    )
    with httpx.Client(transport=transport) as http_client:
        with pytest.raises(PlaceSourceResponseError, match="content type"):
            PlaceAwardsClient(http_client, records_url="https://example.test").fetch_page(
                offset=0
            )

    oversized = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            headers={"content-type": "application/json", "content-length": "10"},
            content=b"{}",
        )
    )
    with httpx.Client(transport=oversized) as http_client:
        client = PlaceAwardsClient(http_client, records_url="https://example.test")
        client.MAX_RESPONSE_BYTES = 2
        with pytest.raises(PlaceSourceResponseError, match="response exceeds"):
            client.fetch_page(offset=0)


def test_collector_emits_all_awards_and_stops_at_checkpoint() -> None:
    first = PlaceAward.model_validate(_award()).model_dump(mode="json")
    second = PlaceAward.model_validate(
        _award(
            nom_attributaire="Other",
            siret_attributaire="99999999999999",
            objet_du_marche="Maintenance réseau",
        )
    ).model_dump(mode="json")
    first_mapping = map_place_award(
        PlaceAward.model_validate(first),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )
    batch = collect_place_awards(
        StubPlaceClient([{"total_count": 2, "results": [first, second]}]),  # type: ignore[arg-type]
        _entry(),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
        checkpoint=PlaceCheckpoint(first_mapping.observation.source_record_key, "2026-08-10"),
    )
    assert batch.not_modified is True
    assert batch.observations == ()

    fresh = collect_place_awards(
        StubPlaceClient([{"total_count": 2, "results": [first, second]}]),  # type: ignore[arg-type]
        _entry(),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )
    assert len(fresh.observations) == 2
    assert len(fresh.procurement) == 2
    assert len(fresh.buyers) == 1


def test_collector_fails_closed_on_policy_schema_and_window() -> None:
    denied = replace(
        _entry(),
        policy=replace(_entry().policy, status=SourceStatus.QUARANTINED),
    )
    with pytest.raises(PlaceCollectionDeniedError, match="source_not_enabled"):
        _collect(StubPlaceClient([]), entry=denied)

    with pytest.raises(PlaceSourceSchemaError, match="schema validation"):
        _collect(StubPlaceClient([{"total_count": 1, "results": [{"bad": True}]}]))

    full_page = [_award(nom_attributaire=f"Awardee {index}") for index in range(100)]
    with pytest.raises(PlaceSourceWindowError, match="checkpoint"):
        collect_place_awards(
            StubPlaceClient([{"total_count": 500, "results": full_page}]),  # type: ignore[arg-type]
            _entry(),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
            checkpoint=PlaceCheckpoint("missing", "2020-01-01"),
            max_pages=1,
        )


def _collect(
    client: StubPlaceClient,
    *,
    entry: SourceRegistryEntry | None = None,
) -> object:
    return collect_place_awards(
        client,  # type: ignore[arg-type]
        entry or _entry(),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/sources.procurement_funding.yml"))
        if entry.policy.id == "place-awards"
    )


def _award(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "annee_de_notification": "2026-01-01",
        "entite_publique": "Ministère exemple",
        "entite_d_achat": "Service des achats",
        "code_postal_entite_d_achat": "75001",
        "nom_attributaire": "Example SAS",
        "siret_attributaire": "12345678901234",
        "date_de_notification": "2026-08-10",
        "code_postal_attributaire": "75002",
        "ville": "Paris",
        "nature_du_marche": "Services",
        "objet_du_marche": "SOC et SIEM",
        "tranche_budgetaire": "100000-500000",
        "montant": 250000,
        "attributaire_est_une_pme": "Oui",
        "geocode_att": [48.85, 2.35],
    }
    payload.update(changes)
    return payload

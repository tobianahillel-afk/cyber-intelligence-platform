from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from cip.adapters.sources.ademe_funding.client import (
    AdemeFundingClient,
    AdemeFundingFetchResult,
    AdemeFundingResponseError,
)
from cip.adapters.sources.ademe_funding.collector import (
    AdemeFundingCheckpoint,
    AdemeFundingCollectionDeniedError,
    AdemeFundingPaginationError,
    AdemeFundingSchemaError,
    collect_ademe_funding,
)
from cip.adapters.sources.ademe_funding.mapper import map_ademe_funding_line
from cip.adapters.sources.ademe_funding.schemas import AdemeFundingLine, AdemeFundingResponse
from cip.modules.corporate_changes.domain.models import (
    ChangeClaimType,
    ChangeEventType,
    OrganizationLinkStatus,
)
from cip.modules.source_governance.domain.models import SourceStatus
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 11, 8, 0, tzinfo=UTC)
BASE_URL = (
    "https://data.ademe.fr/data-fair/api/v1/datasets/"
    "les-aides-financieres-de-l'ademe/lines"
)
SELECT_QUERY = (
    "size=100&select=_id%2CnomBeneficiaire%2Cobjet%2Cnature%2C"
    "dateConvention%2Cmontant"
)


class StubAdemeClient:
    def __init__(self, pages: dict[str, dict[str, object]]) -> None:
        self.pages = pages
        self.urls: list[str] = []

    def first_page_url(self) -> str:
        return f"{BASE_URL}?{SELECT_QUERY}"

    def fetch_url(self, url: str) -> AdemeFundingFetchResult:
        self.urls.append(url)
        return AdemeFundingFetchResult(json.dumps(self.pages[url]).encode(), url)


def test_schema_and_mapper_create_official_unresolved_funding_claim() -> None:
    line = AdemeFundingLine.model_validate(_line())
    observation, claim = map_ademe_funding_line(
        line,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )

    assert line.nom == "Example SAS"
    assert line.date == "2026-08-01"
    assert observation.source_id == "ademe-financial-aid"
    assert observation.source_record_type == "public_funding_award"
    assert claim.event_type is ChangeEventType.FUNDING
    assert claim.claim_type is ChangeClaimType.CONFIRMATION
    assert claim.organization_link_status is OrganizationLinkStatus.UNRESOLVED
    assert claim.organization_id is None
    assert claim.claimed_organization_name == "Example SAS"
    assert claim.event_at is not None


def test_mapper_marks_old_or_unparseable_event_dates_historical() -> None:
    old = AdemeFundingLine.model_validate(_line(dateConvention="2024-01-01"))
    _observation, claim = map_ademe_funding_line(
        old,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )
    assert claim.historical_only is True

    unknown = AdemeFundingLine.model_validate(_line(dateConvention="Période 2026"))
    _observation, claim = map_ademe_funding_line(
        unknown,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )
    assert claim.event_at is None
    assert claim.historical_only is True


def test_schema_rejects_blank_fields_negative_amount_and_negative_total() -> None:
    with pytest.raises(ValidationError):
        AdemeFundingLine.model_validate(_line(nomBeneficiaire=" "))
    with pytest.raises(ValidationError):
        AdemeFundingLine.model_validate(_line(montant=-1))
    with pytest.raises(ValidationError):
        AdemeFundingResponse.model_validate({"total": -1, "results": []})


def test_client_builds_public_selected_field_query() -> None:
    with httpx.Client() as http_client:
        client = AdemeFundingClient(http_client, lines_url=BASE_URL)
        url = client.first_page_url()
    assert "size=100" in url
    assert "nomBeneficiaire" in url
    assert "dateConvention" in url
    assert "select=_id%2CnomBeneficiaire" in url


def test_client_rejects_non_json_and_oversized_response() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, headers={"content-type": "text/html"}, text="bad")
    )
    with (
        httpx.Client(transport=transport) as http_client,
        pytest.raises(AdemeFundingResponseError, match="content type"),
    ):
        AdemeFundingClient(http_client, lines_url=BASE_URL).fetch_url(BASE_URL)

    oversized = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            headers={"content-type": "application/json", "content-length": "10"},
            content=b"{}",
        )
    )
    with httpx.Client(transport=oversized) as http_client:
        client = AdemeFundingClient(http_client, lines_url=BASE_URL)
        client.MAX_RESPONSE_BYTES = 2
        with pytest.raises(AdemeFundingResponseError, match="response exceeds"):
            client.fetch_url(BASE_URL)


def test_collector_follows_safe_cursor_and_persists_next_checkpoint() -> None:
    first_url = f"{BASE_URL}?{SELECT_QUERY}"
    second_url = f"{BASE_URL}?after=cursor-1"
    client = StubAdemeClient(
        {
            first_url: {"total": 2, "results": [_line()], "next": second_url},
            second_url: {
                "total": 2,
                "results": [
                    _line(_id="aid-2", nomBeneficiaire="Other SAS")
                ],
                "next": None,
            },
        }
    )
    batch = collect_ademe_funding(
        client,  # type: ignore[arg-type]
        _entry(),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
        max_pages=1,
    )
    assert len(batch.observations) == 1
    assert len(batch.claims) == 1
    assert batch.checkpoint.next_url == second_url

    resumed = collect_ademe_funding(
        client,  # type: ignore[arg-type]
        _entry(),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
        checkpoint=AdemeFundingCheckpoint(second_url),
        max_pages=1,
    )
    assert resumed.observations[0].source_record_key == "aid-2"
    assert resumed.checkpoint.next_url is None


def test_collector_rejects_policy_schema_and_unsafe_pagination() -> None:
    first_url = f"{BASE_URL}?{SELECT_QUERY}"
    denied = replace(
        _entry(),
        policy=replace(_entry().policy, status=SourceStatus.QUARANTINED),
    )
    with pytest.raises(AdemeFundingCollectionDeniedError, match="source_not_enabled"):
        collect_ademe_funding(
            StubAdemeClient({first_url: {"total": 0, "results": []}}),  # type: ignore[arg-type]
            denied,
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )

    with pytest.raises(AdemeFundingSchemaError, match="schema validation"):
        _collect(StubAdemeClient({first_url: {"bad": True}}))

    malicious = StubAdemeClient(
        {
            first_url: {
                "total": 1,
                "results": [_line()],
                "next": "https://evil.example/lines?after=x",
            }
        }
    )
    with pytest.raises(AdemeFundingPaginationError, match="provider host"):
        collect_ademe_funding(
            malicious,  # type: ignore[arg-type]
            _entry(),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
            max_pages=2,
        )


def _collect(client: StubAdemeClient) -> object:
    return collect_ademe_funding(
        client,  # type: ignore[arg-type]
        _entry(),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/sources.procurement_funding.yml"))
        if entry.policy.id == "ademe-financial-aid"
    )


def _line(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "_id": "aid-1",
        "nomBeneficiaire": "Example SAS",
        "objet": "Programme de transformation industrielle",
        "nature": "aide en numéraire",
        "dateConvention": "2026-08-01",
        "montant": 125000,
    }
    payload.update(changes)
    return payload

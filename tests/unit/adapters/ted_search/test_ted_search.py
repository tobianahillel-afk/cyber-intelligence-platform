from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.ted_search.client import (
    TedSearchClient,
    TedSourceResponseError,
)
from cip.adapters.sources.ted_search.mapper import map_ted_notice
from cip.adapters.sources.ted_search.schemas import TedNotice, TedSearchResponse
from cip.modules.opportunities.domain.entities import SignalType

NOW = datetime(2026, 8, 4, 10, 0, tzinfo=UTC)


def test_client_posts_bounded_active_search() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["body"] = request.read().decode()
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"notices": []},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        result = TedSearchClient(
            http_client,
            search_url="https://api.ted.europa.eu/v3/notices/search",
        ).fetch()

    assert captured["method"] == "POST"
    assert '"scope":"ACTIVE"' in str(captured["body"])
    assert '"limit":100' in str(captured["body"])
    assert TedSearchResponse.model_validate_json(result.body).notices == []


def test_client_rejects_non_json_and_oversized_responses() -> None:
    def wrong_type(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, text="no")

    with (
        httpx.Client(transport=httpx.MockTransport(wrong_type)) as http_client,
        pytest.raises(TedSourceResponseError, match="content type"),
    ):
        TedSearchClient(http_client, search_url="https://example.test/search").fetch()

    def oversized(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "content-type": "application/json",
                "content-length": str(TedSearchClient.MAX_RESPONSE_BYTES + 1),
            },
            content=b"{}",
        )

    with (
        httpx.Client(transport=httpx.MockTransport(oversized)) as http_client,
        pytest.raises(TedSourceResponseError, match="size limit"),
    ):
        TedSearchClient(http_client, search_url="https://example.test/search").fetch()


def test_schema_normalizes_localized_fields_and_dates() -> None:
    notice = TedNotice.model_validate(
        _notice_payload(
            **{
                "notice-title": {"fra": "Supervision SIEM"},
                "buyer-name": {"eng": ["Public Buyer"]},
                "publication-date": "20260804",
                "deadline-receipt-tender-date-lot": ["2026-08-20T12:00:00Z"],
            }
        )
    )

    assert notice.title() == "Supervision SIEM"
    assert notice.buyer() == "Public Buyer"
    assert notice.country() == "FRA"
    assert notice.publication_timestamp() == datetime(2026, 8, 4)
    assert notice.deadline_timestamp() == datetime(2026, 8, 20, 12, tzinfo=UTC)


def test_mapper_creates_deterministic_evidence_backed_projection() -> None:
    notice = TedNotice.model_validate(_notice_payload())
    retention = NOW + timedelta(days=730)

    first = map_ted_notice(
        notice,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=retention,
    )
    second = map_ted_notice(
        notice,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=retention,
    )

    assert first is not None and second is not None
    observation, projection = first
    assert projection.organization.id == second[1].organization.id
    assert projection.evidence.id == second[1].evidence.id
    assert projection.signal.id == second[1].signal.id
    assert projection.organization.country_code == "FR"
    assert projection.signal.signal_type is SignalType.PUBLIC_TENDER
    assert projection.signal.matched_terms == ("siem", "soc")
    assert projection.signal.evidence_id == projection.evidence.id
    assert observation.source_url.endswith("123456-2026/html")
    assert observation.payload_hash_sha256 == projection.evidence.content_hash_sha256


def test_mapper_drops_false_positive_returned_by_remote_search() -> None:
    notice = TedNotice.model_validate(
        _notice_payload(**{"notice-title": {"eng": "Office furniture supply"}})
    )

    assert (
        map_ted_notice(
            notice,
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=30),
        )
        is None
    )


def _notice_payload(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "publication-number": "123456-2026",
        "notice-title": {"eng": "SIEM and SOC managed security service"},
        "buyer-name": {"eng": ["Ville Exemple"]},
        "buyer-country": ["FRA"],
        "publication-date": "2026-08-04",
        "deadline-receipt-tender-date-lot": ["2026-08-20T12:00:00Z"],
        "classification-cpv": ["72000000"],
        "notice-type": ["cn-standard"],
    }
    payload.update(changes)
    return payload

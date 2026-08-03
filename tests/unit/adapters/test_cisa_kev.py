from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.cisa_kev.client import (
    CisaKevCheckpoint,
    CisaKevClient,
    CisaKevFetchResult,
    SourceResponseError,
)
from cip.adapters.sources.cisa_kev.collector import (
    CollectionDeniedError,
    SourceSchemaError,
    collect_cisa_kev,
)
from cip.adapters.sources.cisa_kev.schemas import CisaKevCatalog
from cip.modules.source_governance.infrastructure.registry import load_source_registry

NOW = datetime(2026, 8, 3, 16, 0, tzinfo=UTC)
LATER = NOW + timedelta(days=365)
FEED_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


def catalog_payload(*, count: int = 1) -> bytes:
    return (
        "{"
        '"title":"CISA Known Exploited Vulnerabilities Catalog",'
        '"catalogVersion":"2026.08.03",'
        '"dateReleased":"2026-08-03T15:00:00Z",'
        f'"count":{count},'
        '"vulnerabilities":[{'
        '"cveID":"CVE-2026-12345",'
        '"vendorProject":"Example Vendor",'
        '"product":"Example Product",'
        '"vulnerabilityName":"Example Vulnerability",'
        '"dateAdded":"2026-08-03",'
        '"shortDescription":"A known exploited vulnerability.",'
        '"requiredAction":"Apply vendor mitigations.",'
        '"dueDate":"2026-08-24",'
        '"knownRansomwareCampaignUse":"Unknown",'
        '"notes":"",'
        '"cwes":["CWE-79"]'
        "}]}"
    ).encode()


def cisa_entry():
    return next(
        entry
        for entry in load_source_registry(Path("policies/sources.example.yml"))
        if entry.policy.id == "cisa-kev"
    )


def test_schema_validates_catalog_count_and_dates() -> None:
    catalog = CisaKevCatalog.model_validate_json(catalog_payload())

    assert catalog.count == 1
    assert catalog.vulnerabilities[0].cve_id == "CVE-2026-12345"

    with pytest.raises(ValueError, match="count does not match"):
        CisaKevCatalog.model_validate_json(catalog_payload(count=2))


def test_client_fetches_json_and_conditional_headers() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(request.headers)
        return httpx.Response(
            200,
            content=catalog_payload(),
            headers={
                "content-type": "application/json",
                "etag": '"abc"',
                "last-modified": "Mon, 03 Aug 2026 15:00:00 GMT",
            },
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        result = CisaKevClient(http_client, feed_url=FEED_URL).fetch(
            CisaKevCheckpoint(etag='"old"', last_modified="previous")
        )

    assert result.not_modified is False
    assert result.etag == '"abc"'
    assert captured["if-none-match"] == '"old"'
    assert captured["if-modified-since"] == "previous"


def test_client_handles_not_modified() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(304, headers={"etag": '"same"'})
    )
    checkpoint = CisaKevCheckpoint(etag='"old"', last_modified="previous")

    with httpx.Client(transport=transport) as http_client:
        result = CisaKevClient(http_client, feed_url=FEED_URL).fetch(checkpoint)

    assert result.not_modified is True
    assert result.body is None
    assert result.etag == '"same"'
    assert result.last_modified == "previous"


@pytest.mark.parametrize(
    ("headers", "message"),
    [
        ({"content-type": "text/html"}, "content type"),
        ({"content-type": "application/json", "content-length": "invalid"}, "Content-Length"),
        ({"content-type": "application/json", "content-length": "999"}, "size limit"),
    ],
)
def test_client_rejects_unsafe_response_metadata(
    headers: dict[str, str],
    message: str,
) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=b"{}", headers=headers)
    )
    with httpx.Client(transport=transport) as http_client:
        client = CisaKevClient(http_client, feed_url=FEED_URL)
        client.MAX_RESPONSE_BYTES = 10
        with pytest.raises(SourceResponseError, match=message):
            client.fetch()


def test_client_rejects_actual_oversized_body() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            content=b"01234567890",
            headers={"content-type": "application/json"},
        )
    )
    with httpx.Client(transport=transport) as http_client:
        client = CisaKevClient(http_client, feed_url=FEED_URL)
        client.MAX_RESPONSE_BYTES = 10
        with pytest.raises(SourceResponseError, match="body exceeds"):
            client.fetch()


def test_collector_maps_observation_and_checkpoint() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            content=catalog_payload(),
            headers={"content-type": "application/json", "etag": '"abc"'},
        )
    )
    with httpx.Client(transport=transport) as http_client:
        batch = collect_cisa_kev(
            CisaKevClient(http_client, feed_url=FEED_URL),
            cisa_entry(),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=LATER,
        )

    assert batch.not_modified is False
    assert batch.checkpoint.catalog_version == "2026.08.03"
    assert len(batch.observations) == 1
    assert batch.observations[0].source_record_key == "CVE-2026-12345"
    assert batch.observations[0].classification == "public"


def test_collector_returns_empty_batch_for_not_modified() -> None:
    checkpoint = CisaKevCheckpoint(etag='"old"', catalog_version="2026.08.02")
    transport = httpx.MockTransport(lambda request: httpx.Response(304))
    with httpx.Client(transport=transport) as http_client:
        batch = collect_cisa_kev(
            CisaKevClient(http_client, feed_url=FEED_URL),
            cisa_entry(),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=LATER,
            checkpoint=checkpoint,
        )

    assert batch.not_modified is True
    assert batch.observations == ()
    assert batch.checkpoint.catalog_version == "2026.08.02"


def test_collector_denies_source_before_network() -> None:
    entry = cisa_entry()
    denied = replace(entry, policy=replace(entry.policy, status="paused"))
    transport = httpx.MockTransport(lambda request: pytest.fail("network must not be used"))

    with httpx.Client(transport=transport) as http_client:
        with pytest.raises(CollectionDeniedError, match="source_not_enabled"):
            collect_cisa_kev(
                CisaKevClient(http_client, feed_url=FEED_URL),
                denied,
                collection_job_id=uuid4(),
                collected_at=NOW,
                retention_until=LATER,
            )


def test_collector_reports_schema_drift() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            content=b'{"unexpected":true}',
            headers={"content-type": "application/json"},
        )
    )
    with httpx.Client(transport=transport) as http_client:
        with pytest.raises(SourceSchemaError, match="schema validation"):
            collect_cisa_kev(
                CisaKevClient(http_client, feed_url=FEED_URL),
                cisa_entry(),
                collection_job_id=uuid4(),
                collected_at=NOW,
                retention_until=LATER,
            )


def test_collector_rejects_empty_modified_response() -> None:
    class EmptyClient:
        def fetch(self, checkpoint: CisaKevCheckpoint | None = None) -> CisaKevFetchResult:
            return CisaKevFetchResult(None, None, None, False)

    with pytest.raises(SourceSchemaError, match="no body"):
        collect_cisa_kev(
            cast(CisaKevClient, EmptyClient()),
            cisa_entry(),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=LATER,
        )

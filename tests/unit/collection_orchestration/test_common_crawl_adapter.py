from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.common_crawl_adapter import (
    CommonCrawlIndexAdapter,
)
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 11, 10, 45, tzinfo=UTC)
RETENTION = NOW + timedelta(days=365)
ORG_ID = UUID("86fe6126-5731-5c4d-a206-69a6a736cae5")
POLICY_PATH = Path("policies/sources.search_archives.yml")


def test_common_crawl_uses_latest_collection_and_maps_only_in_scope() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/collinfo.json":
            return _json_response(request, _collections())
        assert request.url.path == "/CC-MAIN-2026-30-index"
        assert request.url.params["url"] == "https://example.com/public/*"
        assert request.url.params["limit"] == "50"
        body = "\n".join(
            [
                json.dumps(_capture(url="https://example.com/public/report")),
                json.dumps(_capture(url="https://example.com/private/secret", digest="OTHER")),
            ]
        )
        return httpx.Response(200, text=body, request=request)

    adapter = CommonCrawlIndexAdapter(
        _entry(),
        (_target(),),
        transport=httpx.MockTransport(handler),
    )
    batch = _collect(adapter)
    assert len(requests) == 2
    assert len(batch.observations) == 1
    assert len(batch.public_footprint_projections) == 1
    projection = batch.public_footprint_projections[0]
    assert projection.claims == ()
    assert projection.resource.canonical_url == "https://example.com/public/report"
    assert projection.resource.retrieval_state.value == "quarantined"
    assert "WARC body not retrieved" in (projection.version.excerpt or "")
    assert batch.checkpoint_payload == {
        "pair_index": 0,
        "crawl_ids": {"common-crawl-live:/public": "CC-MAIN-2026-30"},
    }


def test_common_crawl_skips_capture_query_for_processed_crawl() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _json_response(request, _collections())

    adapter = CommonCrawlIndexAdapter(
        _entry(),
        (_target(),),
        transport=httpx.MockTransport(handler),
    )
    batch = _collect(
        adapter,
        checkpoint_payload={
            "pair_index": 0,
            "crawl_ids": {"common-crawl-live:/public": "CC-MAIN-2026-30"},
        },
    )
    assert len(requests) == 1
    assert batch.not_modified is True
    assert batch.observations == ()


def test_common_crawl_without_enabled_targets_performs_no_network() -> None:
    def fail_network(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be used without a target")

    adapter = CommonCrawlIndexAdapter(
        _entry(),
        (_target(enabled=False),),
        transport=httpx.MockTransport(fail_network),
    )
    batch = _collect(adapter)
    assert batch.not_modified is True
    assert batch.checkpoint_payload == {"pair_index": 0, "crawl_ids": {}}


def test_common_crawl_rejects_invalid_checkpoint_and_provider_endpoint() -> None:
    adapter = CommonCrawlIndexAdapter(
        _entry(),
        (_target(),),
        transport=httpx.MockTransport(lambda request: _json_response(request, _collections())),
    )
    with pytest.raises(AdapterExecutionError) as exc_info:
        _collect(adapter, checkpoint_payload={"pair_index": True, "crawl_ids": {}})
    assert exc_info.value.error_code == "invalid_checkpoint"

    def unsafe_collection(request: httpx.Request) -> httpx.Response:
        payload = _collections()
        payload[1]["cdx-api"] = "https://evil.example/CC-MAIN-2026-30-index"
        return _json_response(request, payload)

    unsafe_adapter = CommonCrawlIndexAdapter(
        _entry(),
        (_target(),),
        transport=httpx.MockTransport(unsafe_collection),
    )
    with pytest.raises(AdapterExecutionError) as unsafe_info:
        _collect(unsafe_adapter)
    assert unsafe_info.value.error_code == "unsafe_source_response"


def test_common_crawl_classifies_schema_and_http_failures() -> None:
    def malformed(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json", request=request)

    adapter = CommonCrawlIndexAdapter(
        _entry(),
        (_target(),),
        transport=httpx.MockTransport(malformed),
    )
    with pytest.raises(AdapterExecutionError) as schema_info:
        _collect(adapter)
    assert schema_info.value.error_code == "source_schema_drift"

    def rate_limited(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, request=request)

    rate_adapter = CommonCrawlIndexAdapter(
        _entry(),
        (_target(),),
        transport=httpx.MockTransport(rate_limited),
    )
    with pytest.raises(AdapterExecutionError) as http_info:
        _collect(rate_adapter)
    assert http_info.value.error_code == "http_429"
    assert http_info.value.retryable is True


def _collections() -> list[dict[str, str]]:
    return [
        {
            "id": "CC-MAIN-2026-25",
            "name": "June 2026 Index",
            "timegate": "https://index.commoncrawl.org/CC-MAIN-2026-25/",
            "cdx-api": "https://index.commoncrawl.org/CC-MAIN-2026-25-index",
            "from": "2026-06-05T21:48:11",
            "to": "2026-06-18T19:32:05",
        },
        {
            "id": "CC-MAIN-2026-30",
            "name": "July 2026 Index",
            "timegate": "https://index.commoncrawl.org/CC-MAIN-2026-30/",
            "cdx-api": "https://index.commoncrawl.org/CC-MAIN-2026-30-index",
            "from": "2026-07-10T07:05:34",
            "to": "2026-07-23T01:13:28",
        },
    ]


def _capture(*, url: str, digest: str = "DIGEST") -> dict[str, str]:
    return {
        "timestamp": "20260715120000",
        "url": url,
        "mime": "text/html",
        "status": "200",
        "digest": digest,
        "length": "1234",
        "offset": "5678",
        "filename": "crawl-data/CC-MAIN-2026-30/segments/example/warc/example.warc.gz",
    }


def _target(*, enabled: bool = True) -> PublicWebTarget:
    return PublicWebTarget(
        id="common-crawl-live",
        organization_id=ORG_ID,
        canonical_name="Controlled Example Target",
        base_url="https://example.com",
        sitemap_urls=("https://example.com/sitemap.xml",),
        feed_urls=(),
        discover_security_txt=False,
        allowed_path_prefixes=("/public",),
        enabled=enabled,
        authorization_reference="sa14-controlled-live-example",
        authorization_reviewed_at=NOW,
        terms_url="https://example.com/",
    )


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(POLICY_PATH)
        if entry.policy.id == "common-crawl-index"
    )


def _collect(
    adapter: CommonCrawlIndexAdapter,
    *,
    checkpoint_payload: dict[str, object] | None = None,
):
    return adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=checkpoint_payload,
        collected_at=NOW,
        retention_until=RETENTION,
    )


def _json_response(request: httpx.Request, payload: object) -> httpx.Response:
    return httpx.Response(200, json=payload, request=request)

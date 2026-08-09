from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.archive_cdx_adapter import (
    InternetArchiveCdxAdapter,
)
from cip.modules.collection_orchestration.application.brave_search_adapter import (
    BraveSearchAdapter,
)
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.public_footprint.domain.models import (
    PublicResourceKind,
    ResourceRetrievalState,
)
from cip.modules.public_footprint.domain.search import SearchQueryTemplate
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 9, 16, 45, tzinfo=UTC)
RETENTION = NOW + timedelta(days=365)
JOB_ID = UUID("00000000-0000-0000-0000-000000000202")
ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000000203")
REGISTRY = Path("policies/sources.search_archives.yml")


def test_brave_search_maps_quarantined_discovery_lead_without_claims() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _json_response(
            {
                "web": {
                    "results": [
                        {
                            "title": "Example security architecture",
                            "url": "https://example.com/security",
                            "description": "Public security information",
                        }
                    ]
                }
            }
        )

    adapter = BraveSearchAdapter(
        _entry("brave-search-api"),
        (_target(),),
        (_template(),),
        token_provider=lambda: "test-token",
        transport=httpx.MockTransport(handler),
    )
    batch = _collect_brave(adapter)

    assert len(batch.observations) == 1
    assert len(batch.public_footprint_projections) == 1
    projection = batch.public_footprint_projections[0]
    assert projection.resource.kind is PublicResourceKind.SEARCH_RESULT
    assert projection.resource.retrieval_state is ResourceRetrievalState.QUARANTINED
    assert projection.claims == ()
    assert requests[0].headers["X-Subscription-Token"] == "test-token"
    assert requests[0].url.params["q"] == '"Example Corp" cybersecurity architecture'


def test_brave_search_fails_closed_when_provider_secret_is_unavailable() -> None:
    adapter = BraveSearchAdapter(
        _entry("brave-search-api"),
        (_target(),),
        (_template(),),
        token_provider=lambda: None,
        transport=httpx.MockTransport(_fail_network),
    )

    with pytest.raises(AdapterExecutionError) as error:
        _collect_brave(adapter)

    assert error.value.error_code == "provider_not_connected"
    assert error.value.retryable is False


def test_brave_search_without_targets_skips_secret_and_network() -> None:
    calls = 0

    def token_provider() -> str:
        nonlocal calls
        calls += 1
        return "unused"

    adapter = BraveSearchAdapter(
        _entry("brave-search-api"),
        (),
        (_template(),),
        token_provider=token_provider,
        transport=httpx.MockTransport(_fail_network),
    )
    batch = _collect_brave(adapter)

    assert batch.not_modified is True
    assert calls == 0


def test_cdx_maps_historical_quarantined_snapshot_without_claims() -> None:
    payload = [
        ["timestamp", "original", "mimetype", "statuscode", "digest", "length"],
        [
            "20240102123456",
            "https://example.com/",
            "text/html",
            "200",
            "ABC123",
            "1234",
        ],
    ]
    adapter = InternetArchiveCdxAdapter(
        _entry("internet-archive-cdx"),
        (_target(),),
        transport=httpx.MockTransport(lambda _request: _json_response(payload)),
    )
    batch = _collect_archive(adapter)

    assert len(batch.observations) == 1
    projection = batch.public_footprint_projections[0]
    assert projection.resource.kind is PublicResourceKind.ARCHIVE_SNAPSHOT
    assert projection.resource.retrieval_state is ResourceRetrievalState.QUARANTINED
    assert projection.claims == ()
    assert "2024-01-02T12:34:56+00:00" in (projection.resource.title or "")


def test_cdx_without_targets_performs_no_network() -> None:
    adapter = InternetArchiveCdxAdapter(
        _entry("internet-archive-cdx"),
        (),
        transport=httpx.MockTransport(_fail_network),
    )
    batch = _collect_archive(adapter)

    assert batch.not_modified is True
    assert batch.observations == ()


def _collect_brave(adapter: BraveSearchAdapter):
    return adapter.collect(
        collection_job_id=JOB_ID,
        checkpoint_payload=None,
        collected_at=NOW,
        retention_until=RETENTION,
    )


def _collect_archive(adapter: InternetArchiveCdxAdapter):
    return adapter.collect(
        collection_job_id=JOB_ID,
        checkpoint_payload=None,
        collected_at=NOW,
        retention_until=RETENTION,
    )


def _entry(source_id: str) -> SourceRegistryEntry:
    entries = {entry.policy.id: entry for entry in load_source_registry(REGISTRY)}
    return entries[source_id]


def _target() -> PublicWebTarget:
    return PublicWebTarget(
        id="example-target",
        organization_id=ORGANIZATION_ID,
        canonical_name="Example Corp",
        base_url="https://example.com/",
        sitemap_urls=("https://example.com/sitemap.xml",),
        allowed_path_prefixes=("/",),
        enabled=True,
        authorization_reference="test-authorization",
        authorization_reviewed_at=NOW,
    )


def _template() -> SearchQueryTemplate:
    return SearchQueryTemplate(
        id="security",
        version=1,
        query_pattern='"{organization}" cybersecurity architecture',
        purpose="corporate-public-footprint",
        enabled=True,
    )


def _json_response(payload: object) -> httpx.Response:
    return httpx.Response(
        200,
        headers={"content-type": "application/json"},
        content=json.dumps(payload).encode("utf-8"),
    )


def _fail_network(_request: httpx.Request) -> httpx.Response:
    raise AssertionError("network must not run")

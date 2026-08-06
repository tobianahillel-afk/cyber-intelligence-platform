from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx

from cip.adapters.sources.public_web.client import (
    PublicWebClient,
    PublicWebFetchResult,
)
from cip.adapters.sources.public_web.mapper import (
    MappedPublicPage,
    PreviousPageState,
    map_public_page,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain import (
    PublicResourceKind,
    ResourceAccessState,
    ResourceRetrievalState,
)
from cip.modules.public_footprint.domain.scope import CrawlUsage

NOW = datetime(2026, 8, 6, 8, 30, tzinfo=UTC)
ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000001210")
RESOURCE_URL = "https://example.com/public/report.pdf"


def test_http_gone_becomes_document_tombstone_and_replays_idempotently() -> None:
    target = _target()
    previous_version_id = uuid4()
    previous = PreviousPageState(
        content_hash_sha256="a" * 64,
        version_id=previous_version_id,
        canonical_url=RESOURCE_URL,
        resource_kind=PublicResourceKind.DOCUMENT,
    )
    with httpx.Client(transport=httpx.MockTransport(_gone_handler)) as raw_client:
        client = PublicWebClient(raw_client)
        robots = client.fetch_robots(target)
        result = client.fetch_page(target, RESOURCE_URL, robots, usage=CrawlUsage())

    assert result.status_code == 410
    assert result.body == b""
    mapped = _map(target, result, previous=previous)
    assert mapped.projection.resource.kind is PublicResourceKind.DOCUMENT
    assert mapped.projection.resource.access_state is ResourceAccessState.UNKNOWN
    assert mapped.projection.resource.retrieval_state is ResourceRetrievalState.TOMBSTONED
    assert mapped.projection.version.byte_size == 0
    assert mapped.projection.version.excerpt == "HTTP 410 tombstone"
    assert mapped.projection.version.supersedes_version_id == previous_version_id
    assert mapped.projection.claims == ()
    assert mapped.observation is not None
    assert mapped.observation.source_record_type == "public_web_tombstone"

    replay = _map(
        target,
        result,
        previous=PreviousPageState(
            content_hash_sha256=mapped.content_hash_sha256,
            version_id=mapped.projection.version.id,
            canonical_url=RESOURCE_URL,
            resource_kind=PublicResourceKind.DOCUMENT,
        ),
    )
    assert replay.observation is None
    assert replay.projection.resource.retrieval_state is ResourceRetrievalState.TOMBSTONED
    assert replay.projection.version.supersedes_version_id is None


def _map(
    target: PublicWebTarget,
    result: PublicWebFetchResult,
    *,
    previous: PreviousPageState,
) -> MappedPublicPage:
    return map_public_page(
        target,
        result,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=30),
        previous=previous,
    )


def _gone_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/robots.txt":
        return httpx.Response(
            200,
            headers={"content-type": "text/plain"},
            content=b"User-agent: *\nAllow: /\n",
        )
    if request.url.path == "/public/report.pdf":
        return httpx.Response(410)
    raise AssertionError(f"unexpected request: {request.url}")


def _target() -> PublicWebTarget:
    return PublicWebTarget(
        id="public-web-example",
        organization_id=ORGANIZATION_ID,
        canonical_name="Example Corp",
        base_url="https://example.com",
        sitemap_urls=("https://example.com/sitemap.xml",),
        allowed_path_prefixes=("/public",),
        enabled=True,
        authorization_reference="approval:public-web-example",
        authorization_reviewed_at=NOW - timedelta(days=1),
        authorization_expires_at=NOW + timedelta(days=30),
        max_pages=10,
        max_total_bytes=2_000_000,
        max_resource_bytes=1_000_000,
        max_redirects=2,
    )

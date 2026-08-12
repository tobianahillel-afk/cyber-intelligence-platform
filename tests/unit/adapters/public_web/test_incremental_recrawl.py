from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.public_web_adapter import PublicWebAdapter
from cip.modules.public_footprint.domain import DiscoveryMethod, ResourceRetrievalState
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_NOW = datetime(2026, 8, 12, 21, 50, tzinfo=UTC)
_ORG_ID = UUID("44444444-4444-4444-4444-444444444444")
_SOURCE_ID = "public-web-incremental-test"


def test_conditional_recrawl_restores_child_frontier_after_parent_304() -> None:
    requests: list[tuple[str, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        validator = request.headers.get("if-none-match")
        requests.append((path, validator))
        if path == "/robots.txt":
            return _response(request, 200, "text/plain", b"User-agent: *\nAllow: /\n")
        if path == "/root":
            if validator == '"root-v1"':
                return httpx.Response(304, headers={"etag": '"root-v1"'}, request=request)
            return _response(
                request,
                200,
                "text/html",
                b'<html><body><a href="/child">child</a></body></html>',
                etag='"root-v1"',
            )
        if path == "/child":
            if validator == '"child-v1"':
                return httpx.Response(304, headers={"etag": '"child-v1"'}, request=request)
            return _response(
                request,
                200,
                "text/html",
                b"<html><body>child</body></html>",
                etag='"child-v1"',
            )
        raise AssertionError(f"unexpected request: {request.url}")

    adapter = _adapter(handler, discover_feeds=False)
    first = _collect(adapter, checkpoint=None, when=_NOW)
    assert len(first.observations) == 2
    pages = first.checkpoint_payload["pages"]
    assert isinstance(pages, dict)
    child = pages["https://example.com/child"]
    assert isinstance(child, dict)
    assert child["etag"] == '"child-v1"'
    assert child["depth"] == 1
    assert child["discovery_method"] == DiscoveryMethod.LINK.value

    requests.clear()
    second = _collect(
        adapter,
        checkpoint=first.checkpoint_payload,
        when=_NOW + timedelta(hours=1),
    )
    assert second.not_modified is True
    assert second.observations == ()
    assert len(second.public_footprint_projections) == 2
    assert all(
        projection.resource.retrieval_state is ResourceRetrievalState.NOT_MODIFIED
        for projection in second.public_footprint_projections
    )
    assert ("/root", '"root-v1"') in requests
    assert ("/child", '"child-v1"') in requests


def test_dynamic_feed_refreshes_when_declaring_html_is_304() -> None:
    feed_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal feed_calls
        path = request.url.path
        validator = request.headers.get("if-none-match")
        if path == "/robots.txt":
            return _response(request, 200, "text/plain", b"User-agent: *\nAllow: /\n")
        if path == "/root":
            if validator == '"root-v1"':
                return httpx.Response(304, headers={"etag": '"root-v1"'}, request=request)
            return _response(
                request,
                200,
                "text/html",
                (
                    b'<html><head><link rel="alternate" type="application/rss+xml" '
                    b'href="/feed.xml"></head><body>root</body></html>'
                ),
                etag='"root-v1"',
            )
        if path == "/feed.xml":
            feed_calls += 1
            item = "item-one" if feed_calls == 1 else "item-two"
            body = (
                "<rss version=\"2.0\"><channel><title>News</title>"
                f"<item><title>{item}</title><link>https://example.com/{item}</link></item>"
                "</channel></rss>"
            ).encode()
            return _response(request, 200, "application/rss+xml", body)
        if path in {"/item-one", "/item-two"}:
            etag = f'"{path[1:]}-v1"'
            if validator == etag:
                return httpx.Response(304, headers={"etag": etag}, request=request)
            return _response(
                request,
                200,
                "text/html",
                f"<html><body>{path}</body></html>".encode(),
                etag=etag,
            )
        raise AssertionError(f"unexpected request: {request.url}")

    adapter = _adapter(handler, discover_feeds=True)
    first = _collect(adapter, checkpoint=None, when=_NOW)
    assert feed_calls == 1
    assert first.checkpoint_payload["feed_urls"] == ["https://example.com/feed.xml"]

    second = _collect(
        adapter,
        checkpoint=first.checkpoint_payload,
        when=_NOW + timedelta(hours=1),
    )
    assert feed_calls == 2
    assert any(
        projection.resource.canonical_url == "https://example.com/item-two"
        for projection in second.public_footprint_projections
    )
    assert len(second.observations) == 1


def _adapter(handler: httpx.MockTransportHandler, *, discover_feeds: bool) -> PublicWebAdapter:
    return PublicWebAdapter(
        _entry(),
        _target(discover_feeds=discover_feeds),
        transport=httpx.MockTransport(handler),
    )


def _collect(
    adapter: PublicWebAdapter,
    *,
    checkpoint: object,
    when: datetime,
):
    assert checkpoint is None or isinstance(checkpoint, dict)
    return adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=checkpoint,
        collected_at=when,
        retention_until=when + timedelta(days=30),
    )


def _target(*, discover_feeds: bool) -> PublicWebTarget:
    return PublicWebTarget(
        id=_SOURCE_ID,
        organization_id=_ORG_ID,
        canonical_name="Example",
        base_url="https://example.com",
        sitemap_urls=(),
        seed_urls=("https://example.com/root",),
        allowed_path_prefixes=("/",),
        enabled=True,
        authorization_reference="approval:test",
        authorization_reviewed_at=_NOW - timedelta(days=1),
        authorization_expires_at=_NOW + timedelta(days=30),
        discover_feeds=discover_feeds,
        max_link_depth=1,
        max_pages=6,
        max_total_bytes=1_000_000,
        max_resource_bytes=100_000,
        max_redirects=1,
    )


def _entry() -> SourceRegistryEntry:
    return SourceRegistryEntry(
        policy=SourcePolicy(
            id=_SOURCE_ID,
            name="Incremental public web test",
            base_url="https://example.com",
            status=SourceStatus.ENABLED,
            source_type=SourceType.STATIC_HTTP,
            owner="Example",
            terms_url=None,
            allowed_data_categories=frozenset(
                {
                    DataCategory.OFFICIAL_DOCUMENT_DISCOVERY,
                    DataCategory.TECHNOLOGY_OBSERVATION,
                }
            ),
            prohibited_data_categories=frozenset(
                {
                    DataCategory.CREDENTIAL,
                    DataCategory.PRIVATE_COMMUNICATION,
                    DataCategory.PRIVATE_PERSONAL_DATA,
                    DataCategory.RESTRICTED_CONTENT,
                    DataCategory.VICTIM_FILE,
                }
            ),
            raw_content_storage=False,
            human_review_required=False,
        ),
        authorization=SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="approval:test",
            reviewed_at=_NOW - timedelta(days=1),
            expires_at=_NOW + timedelta(days=30),
            approved_hosts=frozenset({"example.com"}),
            approved_path_prefixes=("/",),
            approved_purposes=frozenset({"corporate-public-footprint"}),
            automated_collection_allowed=True,
            raw_storage_allowed=False,
        ),
        economics={"cost_model": "free"},
    )


def _response(
    request: httpx.Request,
    status: int,
    mime_type: str,
    body: bytes,
    *,
    etag: str | None = None,
) -> httpx.Response:
    headers = {"content-type": mime_type}
    if etag is not None:
        headers["etag"] = etag
    return httpx.Response(status, headers=headers, content=body, request=request)

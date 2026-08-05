from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

import httpx
import pytest

from cip.adapters.sources.public_web.client import (
    PublicWebClient,
    PublicWebFetchResult,
    PublicWebPolicyDeniedError,
    PublicWebResponseError,
)
from cip.adapters.sources.public_web.mapper import PreviousPageState, map_public_page
from cip.adapters.sources.public_web.parsing import (
    PublicWebParseError,
    contains_credential_marker,
    extract_html,
    parse_sitemap,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain import (
    ResourceAccessState,
    ResourceRetrievalState,
)
from cip.modules.public_footprint.domain.scope import CrawlUsage

NOW = datetime(2026, 8, 5, 22, 0, tzinfo=UTC)
ORGANIZATION_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")


def test_target_requires_public_dns_and_current_authorization() -> None:
    for base_url in (
        "http://127.0.0.1",
        "http://[::1]",
        "https://localhost",
        "https://service.internal",
        "https://printer.local",
    ):
        with pytest.raises(ValueError, match="host"):
            _target(base_url=base_url, sitemap_urls=(f"{base_url}/sitemap.xml",))

    with pytest.raises(ValueError, match="reviewed authorization"):
        _target(authorization_reference=None)

    expired = _target(authorization_expires_at=NOW - timedelta(seconds=1))
    assert not expired.executable_at(NOW)
    active = _target(authorization_expires_at=NOW + timedelta(days=30))
    assert active.executable_at(NOW)


def test_robots_are_loaded_first_and_disallowed_page_is_never_requested() -> None:
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200,
                headers={"content-type": "text/plain"},
                content=b"User-agent: *\nDisallow: /public/blocked\n",
            )
        raise AssertionError(f"unexpected request: {request.url}")

    target = _target()
    with httpx.Client(transport=httpx.MockTransport(handler)) as raw_client:
        client = PublicWebClient(raw_client)
        robots = client.fetch_robots(target)
        assert robots.bytes_fetched > 0
        with pytest.raises(PublicWebPolicyDeniedError, match="robots.txt"):
            client.fetch_page(
                target,
                "https://example.com/public/blocked",
                robots,
                usage=CrawlUsage(),
            )

    assert requested_paths == ["/robots.txt"]


def test_redirect_is_rechecked_before_following_outside_scope() -> None:
    requested_hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200,
                headers={"content-type": "text/plain"},
                content=b"User-agent: *\nAllow: /\n",
            )
        return httpx.Response(
            302,
            headers={"location": "https://outside.example/public/report"},
        )

    target = _target()
    with httpx.Client(transport=httpx.MockTransport(handler)) as raw_client:
        client = PublicWebClient(raw_client)
        robots = client.fetch_robots(target)
        with pytest.raises(PublicWebPolicyDeniedError, match="host_not_allowed"):
            client.fetch_page(
                target,
                "https://example.com/public/report",
                robots,
                usage=CrawlUsage(),
            )

    assert requested_hosts == ["example.com", "example.com"]


def test_robots_and_sitemap_redirects_are_not_followed() -> None:
    def robots_redirect(request: httpx.Request) -> httpx.Response:
        return httpx.Response(301, headers={"location": "/robots-v2.txt"})

    target = _target()
    with (
        httpx.Client(transport=httpx.MockTransport(robots_redirect)) as raw_client,
        pytest.raises(PublicWebResponseError, match="robots.txt redirects"),
    ):
        PublicWebClient(raw_client).fetch_robots(target)

    def sitemap_redirect(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200,
                headers={"content-type": "text/plain"},
                content=b"User-agent: *\nAllow: /\n",
            )
        return httpx.Response(302, headers={"location": "/sitemap-v2.xml"})

    with httpx.Client(transport=httpx.MockTransport(sitemap_redirect)) as raw_client:
        client = PublicWebClient(raw_client)
        robots = client.fetch_robots(target)
        with pytest.raises(PublicWebResponseError, match="sitemap redirects"):
            client.fetch_sitemap(target, target.sitemap_urls[0], robots)


def test_response_mime_and_size_are_bounded() -> None:
    page_body = b"x" * 101

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200,
                headers={"content-type": "text/plain"},
                content=b"User-agent: *\nAllow: /\n",
            )
        return httpx.Response(
            200,
            headers={"content-type": "image/png", "content-length": "101"},
            content=page_body,
        )

    target = _target(max_resource_bytes=100)
    with httpx.Client(transport=httpx.MockTransport(handler)) as raw_client:
        client = PublicWebClient(raw_client)
        robots = client.fetch_robots(target)
        with pytest.raises(PublicWebResponseError, match="size limit"):
            client.fetch_page(
                target,
                "https://example.com/public/report",
                robots,
                usage=CrawlUsage(),
            )


def test_sitemap_filters_scope_duplicates_and_external_urls() -> None:
    sitemap = b"""<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/public/a</loc><lastmod>2026-08-01</lastmod></url>
  <url><loc>https://example.com/public/a</loc></url>
  <url><loc>https://example.com/private/b</loc></url>
  <url><loc>https://outside.example/public/c</loc></url>
</urlset>
"""
    entries = parse_sitemap(sitemap, _target())

    assert len(entries) == 1
    assert entries[0].url == "https://example.com/public/a"
    assert entries[0].last_modified_at == datetime(2026, 8, 1, tzinfo=UTC)

    with pytest.raises(PublicWebParseError, match="DTD"):
        parse_sitemap(
            b"<!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><urlset/>",
            _target(),
        )


def test_html_directives_and_secret_markers_suppress_indexing() -> None:
    extracted = extract_html(
        b"""<html lang="en"><head><title> Security </title>
<meta name="robots" content="noindex,noarchive"></head>
<body>Uses Microsoft Sentinel and zero trust.<script>secret()</script></body></html>"""
    )
    assert extracted.title == "Security"
    assert extracted.language == "en"
    assert extracted.noindex
    assert extracted.noarchive
    assert extracted.excerpt is None
    assert "secret" not in extracted.text
    assert contains_credential_marker(b"-----BEGIN PRIVATE KEY-----")

    result = _result(
        body=(
            b"<html><head><meta name='robots' content='noindex'></head>"
            b"<body>Uses Microsoft Sentinel and zero trust.</body></html>"
        )
    )
    mapped = map_public_page(
        _target(),
        result,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=30),
        previous=None,
    )
    assert mapped.projection.claims == ()
    assert mapped.projection.version.excerpt is None
    assert mapped.projection.version.extracted_text_hash_sha256 is None


def test_mapper_quarantines_credentials_and_versions_redirect_changes() -> None:
    target = _target()
    secret_result = _result(body=b"-----BEGIN PRIVATE KEY-----")
    quarantined = map_public_page(
        target,
        secret_result,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=30),
        previous=None,
    )
    assert quarantined.projection.resource.access_state is ResourceAccessState.UNKNOWN
    assert (
        quarantined.projection.resource.retrieval_state
        is ResourceRetrievalState.QUARANTINED
    )
    assert quarantined.projection.claims == ()
    assert quarantined.projection.version.excerpt is None

    body = b"<html><body>Uses Microsoft Sentinel.</body></html>"
    previous_id = uuid4()
    changed_redirect = map_public_page(
        target,
        _result(body=body, fetched_url="https://example.com/public/new"),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=30),
        previous=PreviousPageState(
            content_hash_sha256=sha256(body).hexdigest(),
            version_id=previous_id,
            canonical_url="https://example.com/public/old",
        ),
    )
    assert changed_redirect.observation is not None
    assert (
        changed_redirect.projection.resource.retrieval_state
        is ResourceRetrievalState.CHANGED
    )
    assert changed_redirect.projection.version.supersedes_version_id is None

    unchanged = map_public_page(
        target,
        _result(body=body),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=30),
        previous=PreviousPageState(
            content_hash_sha256=sha256(body).hexdigest(),
            version_id=previous_id,
            canonical_url="https://example.com/public/report",
        ),
    )
    assert unchanged.observation is None
    assert unchanged.projection.resource.retrieval_state is ResourceRetrievalState.NOT_MODIFIED


def _target(
    *,
    base_url: str = "https://example.com",
    sitemap_urls: tuple[str, ...] = ("https://example.com/sitemap.xml",),
    authorization_reference: str | None = "approval:public-web-example",
    authorization_expires_at: datetime | None = None,
    max_resource_bytes: int = 1_000_000,
) -> PublicWebTarget:
    return PublicWebTarget(
        id="public-web-example",
        organization_id=ORGANIZATION_ID,
        canonical_name="Example Corp",
        base_url=base_url,
        sitemap_urls=sitemap_urls,
        allowed_path_prefixes=("/public",),
        enabled=True,
        authorization_reference=authorization_reference,
        authorization_reviewed_at=NOW - timedelta(days=1),
        authorization_expires_at=authorization_expires_at,
        max_pages=10,
        max_total_bytes=2_000_000,
        max_resource_bytes=max_resource_bytes,
        max_redirects=2,
    )


def _result(
    *,
    body: bytes,
    fetched_url: str = "https://example.com/public/report",
) -> PublicWebFetchResult:
    return PublicWebFetchResult(
        requested_url="https://example.com/public/report",
        fetched_url=fetched_url,
        body=body,
        mime_type="text/html",
        etag=None,
        last_modified=None,
        redirects=0,
    )

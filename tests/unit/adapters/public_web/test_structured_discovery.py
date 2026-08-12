from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx

from cip.adapters.sources.public_web.client import PublicWebClient
from cip.adapters.sources.public_web.collector import collect_public_web_target
from cip.adapters.sources.public_web.link_discovery import extract_public_feed_links
from cip.adapters.sources.public_web.parsing import parse_sitemap_document
from cip.adapters.sources.public_web.provisioning import (
    AutomaticPublicWebPolicy,
    provision_public_web_target,
)
from cip.modules.organizations.domain.entities import Organization
from cip.modules.public_footprint.domain import DiscoveryMethod

_NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
_ORG_ID = UUID("15712d0d-9054-50b4-8a26-e25d9ea1f509")


def _target_and_entry():
    organization = Organization(
        id=_ORG_ID,
        canonical_name="Example Research",
        website_url="https://example.com/",
        created_at=_NOW,
        updated_at=_NOW,
    )
    provisioned = provision_public_web_target(
        organization,
        AutomaticPublicWebPolicy(
            authorization_reference="sa16-l03-test",
            reviewed_at=_NOW,
            max_link_depth=0,
            discover_sitemaps=True,
            discover_feeds=True,
            max_sitemap_depth=1,
            max_sitemaps=4,
            max_feeds=2,
            max_pages=5,
            max_total_bytes=200_000,
            max_resource_bytes=50_000,
            max_redirects=0,
        ),
        first_crawl_at=_NOW,
    )
    return replace(provisioned.target, discover_security_txt=False), provisioned.source_entry


def test_feed_link_discovery_requires_declared_alternate_type() -> None:
    body = b"""
    <html><head>
      <link rel="alternate" type="application/rss+xml" href="/feed.xml">
      <link rel="alternate stylesheet" type="application/atom+xml" href="/atom.xml">
      <link rel="alternate" type="text/html" href="/not-feed">
      <link rel="stylesheet" type="application/rss+xml" href="/also-not-feed">
    </head></html>
    """

    assert extract_public_feed_links(
        body,
        base_url="https://example.com/",
        max_feeds=5,
    ) == (
        "https://example.com/feed.xml",
        "https://example.com/atom.xml",
    )


def test_sitemap_index_parser_bounds_and_filters_children() -> None:
    target, _ = _target_and_entry()
    body = b"""
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <sitemap><loc>https://example.com/a.xml</loc></sitemap>
      <sitemap><loc>https://outside.example/b.xml</loc></sitemap>
      <sitemap><loc>https://example.com/a.xml#duplicate</loc></sitemap>
      <sitemap><loc>https://example.com/c.xml</loc></sitemap>
    </sitemapindex>
    """

    document = parse_sitemap_document(
        body,
        target,
        max_entries=5,
        max_child_sitemaps=2,
    )

    assert document.entries == ()
    assert document.child_sitemaps == (
        "https://example.com/a.xml",
        "https://example.com/c.xml",
    )


def test_collection_traverses_robots_sitemap_index_and_discovered_feed() -> None:
    target, entry = _target_and_entry()
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        requested.append(url)
        if url == "https://example.com/robots.txt":
            return httpx.Response(
                200,
                headers={"content-type": "text/plain"},
                text=(
                    "User-agent: *\nAllow: /\n"
                    "Sitemap: https://example.com/sitemap-index.xml\n"
                    "Sitemap: https://outside.example/ignored.xml\n"
                ),
                request=request,
            )
        if url == "https://example.com/sitemap-index.xml":
            return httpx.Response(
                200,
                headers={"content-type": "application/xml"},
                text=(
                    '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                    "<sitemap><loc>https://example.com/nested.xml</loc></sitemap>"
                    "</sitemapindex>"
                ),
                request=request,
            )
        if url == "https://example.com/nested.xml":
            return httpx.Response(
                200,
                headers={"content-type": "application/xml"},
                text=(
                    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                    "<url><loc>https://example.com/from-sitemap</loc></url>"
                    "</urlset>"
                ),
                request=request,
            )
        if url == "https://example.com/":
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text=(
                    "<html><head><title>Root</title>"
                    '<link rel="alternate" type="application/rss+xml" href="/feed.xml">'
                    "</head><body>Root</body></html>"
                ),
                request=request,
            )
        if url == "https://example.com/feed.xml":
            return httpx.Response(
                200,
                headers={"content-type": "application/rss+xml"},
                text=(
                    "<rss version=\"2.0\"><channel><title>News</title>"
                    "<item><title>Feed item</title>"
                    "<link>https://example.com/from-feed</link></item>"
                    "</channel></rss>"
                ),
                request=request,
            )
        if url in {
            "https://example.com/from-sitemap",
            "https://example.com/from-feed",
        }:
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text=f"<html><title>{url}</title><body>ok</body></html>",
                request=request,
            )
        raise AssertionError(f"unexpected request: {url}")

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        batch = collect_public_web_target(
            PublicWebClient(http_client),
            entry,
            target,
            collection_job_id=uuid4(),
            collected_at=_NOW,
            retention_until=_NOW + timedelta(days=30),
        )

    resources = {projection.resource.canonical_url: projection for projection in batch.projections}
    assert set(resources) == {
        "https://example.com/",
        "https://example.com/from-sitemap",
        "https://example.com/from-feed",
    }
    assert (
        resources["https://example.com/from-sitemap"].resource.discovery_method
        is DiscoveryMethod.SITEMAP
    )
    assert (
        resources["https://example.com/from-feed"].resource.discovery_method
        is DiscoveryMethod.FEED
    )
    assert resources["https://example.com/from-sitemap"].version.source_locator == (
        "https://example.com/nested.xml"
    )
    assert resources["https://example.com/from-feed"].version.source_locator == (
        "https://example.com/feed.xml"
    )
    assert "https://outside.example/ignored.xml" not in requested
    assert requested.count("https://example.com/nested.xml") == 1
    assert requested.count("https://example.com/feed.xml") == 1

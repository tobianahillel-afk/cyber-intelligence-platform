from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx

from cip.adapters.sources.public_web.client import PublicWebClient
from cip.adapters.sources.public_web.collector import collect_public_web_target
from cip.adapters.sources.public_web.provisioning import (
    AutomaticPublicWebPolicy,
    provision_public_web_target,
)
from cip.modules.organizations.domain.entities import Organization
from cip.modules.public_footprint.domain import DiscoveryMethod
from cip.modules.public_footprint.domain.url_identity import same_origin

_DOCS_ORG_ID = UUID("65aa3ec1-1c46-5f64-9192-591abae9ca0a")
_BLOG_ORG_ID = UUID("3679ab63-e441-5445-bdb2-5ec2f760f752")


def main() -> None:
    now = datetime.now(UTC)
    sitemap_count = _run_sitemap_case(now)
    feed_count = _run_feed_case(now)
    print(
        "SA-16 L03 live validation passed: "
        f"robots_sitemap_pages={sitemap_count} html_feed_pages={feed_count}"
    )


def _run_sitemap_case(now: datetime) -> int:
    origin = "https://docs.python.org/"
    organization = Organization(
        id=_DOCS_ORG_ID,
        canonical_name="Python Documentation",
        website_url=origin,
        created_at=now,
        updated_at=now,
    )
    provisioned = provision_public_web_target(
        organization,
        AutomaticPublicWebPolicy(
            authorization_reference="sa16-l03-python-docs-sitemap",
            reviewed_at=now,
            max_link_depth=0,
            discover_sitemaps=True,
            discover_feeds=False,
            max_sitemap_depth=2,
            max_sitemaps=8,
            max_feeds=1,
            max_pages=5,
            max_total_bytes=5_000_000,
            max_resource_bytes=1_000_000,
            max_redirects=1,
        ),
        first_crawl_at=now,
    )
    target = replace(provisioned.target, discover_security_txt=False)
    with httpx.Client(timeout=30.0) as http_client:
        batch = collect_public_web_target(
            PublicWebClient(http_client),
            provisioned.source_entry,
            target,
            collection_job_id=uuid4(),
            collected_at=now,
            retention_until=now + timedelta(days=365),
        )
    sitemap_pages = [
        projection
        for projection in batch.projections
        if projection.resource.discovery_method is DiscoveryMethod.SITEMAP
    ]
    if not sitemap_pages:
        raise RuntimeError("SA16-L03 did not traverse a robots-declared Python docs sitemap")
    if any(not same_origin(origin, item.resource.canonical_url) for item in batch.projections):
        raise RuntimeError("SA16-L03 sitemap traversal escaped the approved origin")
    if any(item.version.source_locator is None for item in sitemap_pages):
        raise RuntimeError("SA16-L03 sitemap page lost its sitemap source locator")
    return len(sitemap_pages)


def _run_feed_case(now: datetime) -> int:
    origin = "https://blog.python.org/"
    organization = Organization(
        id=_BLOG_ORG_ID,
        canonical_name="Python Insider",
        website_url=origin,
        created_at=now,
        updated_at=now,
    )
    provisioned = provision_public_web_target(
        organization,
        AutomaticPublicWebPolicy(
            authorization_reference="sa16-l03-python-insider-feed",
            reviewed_at=now,
            max_link_depth=0,
            discover_sitemaps=False,
            discover_feeds=True,
            max_sitemap_depth=0,
            max_sitemaps=1,
            max_feeds=3,
            max_pages=5,
            max_total_bytes=4_000_000,
            max_resource_bytes=1_000_000,
            max_redirects=1,
        ),
        first_crawl_at=now,
    )
    target = replace(provisioned.target, discover_security_txt=False)
    with httpx.Client(timeout=30.0) as http_client:
        batch = collect_public_web_target(
            PublicWebClient(http_client),
            provisioned.source_entry,
            target,
            collection_job_id=uuid4(),
            collected_at=now,
            retention_until=now + timedelta(days=365),
        )
    feed_pages = [
        projection
        for projection in batch.projections
        if projection.resource.discovery_method is DiscoveryMethod.FEED
    ]
    if not feed_pages:
        raise RuntimeError("SA16-L03 did not traverse an HTML-declared Python Insider feed")
    if any(not same_origin(origin, item.resource.canonical_url) for item in batch.projections):
        raise RuntimeError("SA16-L03 feed traversal escaped the approved origin")
    if any(item.version.source_locator is None for item in feed_pages):
        raise RuntimeError("SA16-L03 feed page lost its feed source locator")
    return len(feed_pages)


if __name__ == "__main__":
    main()

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from cip.adapters.sources.public_web.client import (
    PublicWebClient,
    PublicWebFetchResult,
    RobotsRules,
)
from cip.adapters.sources.public_web.collection_policy import (
    authorize_public_web_url,
    checked_total_bytes,
)
from cip.adapters.sources.public_web.feed_parsing import parse_public_feed
from cip.adapters.sources.public_web.link_discovery import (
    extract_public_feed_links,
    extract_public_html_links,
)
from cip.adapters.sources.public_web.parsing import parse_sitemap_document
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain import DiscoveryMethod
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.public_footprint.domain.url_identity import same_origin
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


@dataclass(frozen=True, slots=True)
class PublicWebDiscoveryCandidate:
    url: str
    discovery_method: DiscoveryMethod
    source_locator: str | None = None
    security_txt: bool = False
    depth: int = 0


def discover_initial_candidates(
    client: PublicWebClient,
    entry: SourceRegistryEntry,
    target: PublicWebTarget,
    robots: RobotsRules,
    *,
    now: datetime,
    initial_bytes: int,
) -> tuple[tuple[PublicWebDiscoveryCandidate, ...], int, set[str]]:
    candidates: list[PublicWebDiscoveryCandidate] = []
    seen: set[str] = set()
    total_bytes = checked_total_bytes(target, initial_bytes)
    for seed_url in target.seed_urls:
        append_candidate(
            candidates,
            seen,
            PublicWebDiscoveryCandidate(
                url=seed_url,
                discovery_method=DiscoveryMethod.DIRECT,
            ),
            max_pages=target.max_pages,
        )
    if target.discover_security_txt:
        append_candidate(
            candidates,
            seen,
            PublicWebDiscoveryCandidate(
                url=target.security_txt_url,
                discovery_method=DiscoveryMethod.DIRECT,
                security_txt=True,
            ),
            max_pages=target.max_pages,
        )
    total_bytes = _discover_sitemap_candidates(
        client,
        entry,
        target,
        robots,
        candidates,
        seen,
        now=now,
        total_bytes=total_bytes,
    )
    seen_feeds = set(target.feed_urls)
    for feed_url in target.feed_urls:
        if len(candidates) >= target.max_pages:
            break
        total_bytes = _consume_feed(
            client,
            entry,
            target,
            robots,
            feed_url,
            candidates,
            seen,
            now=now,
            total_bytes=total_bytes,
            discovered=False,
        )
    return tuple(candidates), total_bytes, seen_feeds


def discover_html_feeds(
    client: PublicWebClient,
    entry: SourceRegistryEntry,
    target: PublicWebTarget,
    robots: RobotsRules,
    fetched: PublicWebFetchResult,
    candidates: list[PublicWebDiscoveryCandidate],
    seen: set[str],
    seen_feeds: set[str],
    *,
    usage: CrawlUsage,
    now: datetime,
) -> CrawlUsage:
    remaining_feeds = target.max_feeds - len(seen_feeds)
    if (
        not target.discover_feeds
        or fetched.mime_type != "text/html"
        or remaining_feeds <= 0
        or len(candidates) >= target.max_pages
    ):
        return usage
    feed_urls = extract_public_feed_links(
        fetched.body,
        base_url=fetched.fetched_url,
        max_feeds=remaining_feeds,
    )
    total_bytes = usage.bytes_fetched
    for feed_url in feed_urls:
        if feed_url in seen_feeds or not same_origin(target.base_url, feed_url):
            continue
        seen_feeds.add(feed_url)
        total_bytes = _consume_feed(
            client,
            entry,
            target,
            robots,
            feed_url,
            candidates,
            seen,
            now=now,
            total_bytes=total_bytes,
            discovered=True,
        )
        if len(seen_feeds) >= target.max_feeds or len(candidates) >= target.max_pages:
            break
    return CrawlUsage(pages_fetched=usage.pages_fetched, bytes_fetched=total_bytes)


def discover_recursive_links(
    target: PublicWebTarget,
    candidate: PublicWebDiscoveryCandidate,
    fetched: PublicWebFetchResult,
    candidates: list[PublicWebDiscoveryCandidate],
    seen: set[str],
) -> None:
    child_depth = candidate.depth + 1
    remaining = target.max_pages - len(candidates)
    if (
        fetched.mime_type != "text/html"
        or child_depth > target.max_link_depth
        or remaining <= 0
    ):
        return
    links = extract_public_html_links(
        fetched.body,
        base_url=fetched.fetched_url,
        max_links=remaining,
    )
    for link in links:
        if not same_origin(target.base_url, link):
            continue
        decision = target.crawl_scope.evaluate_target(
            link,
            depth=child_depth,
            redirects=0,
            usage=CrawlUsage(),
        )
        if not decision.allowed:
            continue
        append_candidate(
            candidates,
            seen,
            PublicWebDiscoveryCandidate(
                url=link,
                discovery_method=DiscoveryMethod.LINK,
                source_locator=fetched.fetched_url,
                depth=child_depth,
            ),
            max_pages=target.max_pages,
        )


def append_candidate(
    candidates: list[PublicWebDiscoveryCandidate],
    seen: set[str],
    candidate: PublicWebDiscoveryCandidate,
    *,
    max_pages: int,
) -> None:
    if len(candidates) >= max_pages or candidate.url in seen:
        return
    seen.add(candidate.url)
    candidates.append(candidate)


def _discover_sitemap_candidates(
    client: PublicWebClient,
    entry: SourceRegistryEntry,
    target: PublicWebTarget,
    robots: RobotsRules,
    candidates: list[PublicWebDiscoveryCandidate],
    seen: set[str],
    *,
    now: datetime,
    total_bytes: int,
) -> int:
    queue: list[tuple[str, int, bool]] = [(url, 0, False) for url in target.sitemap_urls]
    if target.discover_sitemaps:
        queue.extend((url, 0, True) for url in robots.sitemap_urls)
    seen_sitemaps: set[str] = set()
    index = 0
    while index < len(queue) and len(seen_sitemaps) < target.max_sitemaps:
        if len(candidates) >= target.max_pages:
            break
        sitemap_url, depth, discovered = queue[index]
        index += 1
        if sitemap_url in seen_sitemaps:
            continue
        seen_sitemaps.add(sitemap_url)
        authorize_public_web_url(entry, sitemap_url, now=now)
        sitemap = client.fetch_sitemap(
            target,
            sitemap_url,
            robots,
            discovered=discovered,
        )
        total_bytes = checked_total_bytes(target, total_bytes + len(sitemap.body))
        remaining_pages = target.max_pages - len(candidates)
        remaining_sitemaps = target.max_sitemaps - len(seen_sitemaps)
        document = parse_sitemap_document(
            sitemap.body,
            target,
            max_entries=max(1, remaining_pages),
            max_child_sitemaps=max(1, remaining_sitemaps),
        )
        for sitemap_entry in document.entries:
            append_candidate(
                candidates,
                seen,
                PublicWebDiscoveryCandidate(
                    url=sitemap_entry.url,
                    discovery_method=DiscoveryMethod.SITEMAP,
                    source_locator=sitemap_url,
                ),
                max_pages=target.max_pages,
            )
        if depth >= target.max_sitemap_depth or remaining_sitemaps <= 0:
            continue
        for child_url in document.child_sitemaps:
            if child_url in seen_sitemaps or len(queue) >= target.max_sitemaps:
                continue
            queue.append((child_url, depth + 1, True))
    return total_bytes


def _consume_feed(
    client: PublicWebClient,
    entry: SourceRegistryEntry,
    target: PublicWebTarget,
    robots: RobotsRules,
    feed_url: str,
    candidates: list[PublicWebDiscoveryCandidate],
    seen: set[str],
    *,
    now: datetime,
    total_bytes: int,
    discovered: bool,
) -> int:
    authorize_public_web_url(entry, feed_url, now=now)
    feed = client.fetch_feed(target, feed_url, robots, discovered=discovered)
    total_bytes = checked_total_bytes(target, total_bytes + len(feed.body))
    remaining = target.max_pages - len(candidates)
    if remaining <= 0:
        return total_bytes
    for feed_entry in parse_public_feed(feed.body, target, max_entries=remaining):
        append_candidate(
            candidates,
            seen,
            PublicWebDiscoveryCandidate(
                url=feed_entry.url,
                discovery_method=DiscoveryMethod.FEED,
                source_locator=feed_url,
            ),
            max_pages=target.max_pages,
        )
    return total_bytes

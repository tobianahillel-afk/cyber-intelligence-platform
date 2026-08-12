from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin

from cip.modules.public_footprint.domain.url_identity import CanonicalUrl

_FEED_TYPES = {
    "application/atom+xml",
    "application/rss+xml",
}


class _DiscoveryParser(HTMLParser):
    def __init__(self, *, max_links: int, max_feeds: int) -> None:
        super().__init__(convert_charrefs=True)
        self._max_links = max_links
        self._max_feeds = max_feeds
        self.links: list[str] = []
        self.feeds: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        normalized = tag.casefold()
        values = {name.casefold(): value for name, value in attrs}
        href = values.get("href")
        if href is None or not href.strip():
            return
        if normalized == "a" and len(self.links) < self._max_links:
            rel = values.get("rel") or ""
            if "nofollow" not in {part.casefold() for part in rel.split()}:
                self.links.append(href)
            return
        if normalized != "link" or len(self.feeds) >= self._max_feeds:
            return
        rel_tokens = {part.casefold() for part in (values.get("rel") or "").split()}
        media_type = (values.get("type") or "").split(";", 1)[0].strip().casefold()
        if "alternate" in rel_tokens and media_type in _FEED_TYPES:
            self.feeds.append(href)


def extract_public_html_links(
    body: bytes,
    *,
    base_url: str,
    max_links: int,
) -> tuple[str, ...]:
    parser = _parse(body, max_links=max_links, max_feeds=0)
    return _canonicalize(parser.links, base_url=base_url, limit=max_links)


def extract_public_feed_links(
    body: bytes,
    *,
    base_url: str,
    max_feeds: int,
) -> tuple[str, ...]:
    parser = _parse(body, max_links=0, max_feeds=max_feeds)
    return _canonicalize(parser.feeds, base_url=base_url, limit=max_feeds)


def _parse(body: bytes, *, max_links: int, max_feeds: int) -> _DiscoveryParser:
    if max_links < 0 or max_feeds < 0:
        raise ValueError("discovery limits must not be negative")
    parser = _DiscoveryParser(max_links=max_links, max_feeds=max_feeds)
    parser.feed(body.decode("utf-8", errors="replace"))
    parser.close()
    return parser


def _canonicalize(
    values: list[str],
    *,
    base_url: str,
    limit: int,
) -> tuple[str, ...]:
    if limit < 1:
        return ()
    discovered: list[str] = []
    seen: set[str] = set()
    for value in values:
        try:
            canonical = CanonicalUrl(urljoin(base_url, value)).value
        except (TypeError, ValueError):
            continue
        if canonical in seen:
            continue
        seen.add(canonical)
        discovered.append(canonical)
        if len(discovered) >= limit:
            break
    return tuple(discovered)

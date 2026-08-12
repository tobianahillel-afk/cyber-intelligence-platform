from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from xml.etree import ElementTree

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl

_FORBIDDEN_XML_MARKERS = (b"<!DOCTYPE", b"<!ENTITY")
_SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(rb"\bghp_[A-Za-z0-9]{36}\b"),
    re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
)


class PublicWebParseError(RuntimeError):
    """A bounded public document could not be parsed safely."""


@dataclass(frozen=True, slots=True)
class SitemapEntry:
    url: str
    last_modified_at: datetime | None


@dataclass(frozen=True, slots=True)
class SitemapDocument:
    entries: tuple[SitemapEntry, ...]
    child_sitemaps: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExtractedHtml:
    title: str | None
    language: str | None
    text: str
    noindex: bool
    noarchive: bool

    @property
    def excerpt(self) -> str | None:
        if self.noindex or self.noarchive or not self.text:
            return None
        return self.text[:1_000]


def parse_sitemap(
    body: bytes,
    target: PublicWebTarget,
    *,
    max_entries: int | None = None,
) -> tuple[SitemapEntry, ...]:
    document = parse_sitemap_document(
        body,
        target,
        max_entries=max_entries,
        max_child_sitemaps=target.max_sitemaps,
    )
    if document.child_sitemaps:
        raise PublicWebParseError("sitemap index requires recursive traversal")
    return document.entries


def parse_sitemap_document(
    body: bytes,
    target: PublicWebTarget,
    *,
    max_entries: int | None = None,
    max_child_sitemaps: int | None = None,
) -> SitemapDocument:
    upper = body.upper()
    if any(marker in upper for marker in _FORBIDDEN_XML_MARKERS):
        raise PublicWebParseError("sitemap DTD and entities are not allowed")
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as exc:
        raise PublicWebParseError("invalid sitemap XML") from exc
    root_name = _local_name(root.tag)
    if root_name not in {"urlset", "sitemapindex"}:
        raise PublicWebParseError("unsupported sitemap document root")
    entry_limit = max_entries or target.max_pages
    sitemap_limit = max_child_sitemaps or target.max_sitemaps
    if not 1 <= entry_limit <= target.max_pages:
        raise ValueError("sitemap entry limit must fit the target page budget")
    if not 1 <= sitemap_limit <= target.max_sitemaps:
        raise ValueError("child sitemap limit must fit the target sitemap budget")
    if root_name == "urlset":
        return SitemapDocument(
            entries=_parse_urlset(root, target, limit=entry_limit),
            child_sitemaps=(),
        )
    return SitemapDocument(
        entries=(),
        child_sitemaps=_parse_sitemap_index(root, target, limit=sitemap_limit),
    )


def _parse_urlset(
    root: ElementTree.Element,
    target: PublicWebTarget,
    *,
    limit: int,
) -> tuple[SitemapEntry, ...]:
    entries: list[SitemapEntry] = []
    seen: set[str] = set()
    for node in root:
        if _local_name(node.tag) != "url":
            continue
        location = _child_text(node, "loc")
        if location is None:
            continue
        try:
            canonical = CanonicalUrl(location).value
        except ValueError:
            continue
        decision = target.crawl_scope.evaluate_target(
            canonical,
            depth=0,
            redirects=0,
            usage=CrawlUsage(pages_fetched=len(entries)),
        )
        if not decision.allowed or canonical in seen:
            continue
        seen.add(canonical)
        entries.append(
            SitemapEntry(
                url=canonical,
                last_modified_at=_parse_optional_timestamp(_child_text(node, "lastmod")),
            )
        )
        if len(entries) == limit:
            break
    return tuple(entries)


def _parse_sitemap_index(
    root: ElementTree.Element,
    target: PublicWebTarget,
    *,
    limit: int,
) -> tuple[str, ...]:
    sitemaps: list[str] = []
    seen: set[str] = set()
    for node in root:
        if _local_name(node.tag) != "sitemap":
            continue
        location = _child_text(node, "loc")
        if location is None:
            continue
        try:
            canonical = CanonicalUrl(location).value
        except ValueError:
            continue
        decision = target.crawl_scope.evaluate_target(
            canonical,
            depth=0,
            redirects=0,
            usage=CrawlUsage(),
        )
        if not decision.allowed or canonical in seen:
            continue
        seen.add(canonical)
        sitemaps.append(canonical)
        if len(sitemaps) == limit:
            break
    return tuple(sitemaps)


def extract_html(body: bytes, *, max_text_chars: int = 20_000) -> ExtractedHtml:
    if max_text_chars < 1 or max_text_chars > 100_000:
        raise ValueError("max_text_chars must be between 1 and 100000")
    parser = _BoundedHtmlParser(max_text_chars=max_text_chars)
    parser.feed(body.decode("utf-8", errors="replace"))
    parser.close()
    return ExtractedHtml(
        title=_normalize_optional(parser.title),
        language=_normalize_optional(parser.language),
        text=" ".join(" ".join(parser.text_parts).split())[:max_text_chars],
        noindex="noindex" in parser.robots_directives,
        noarchive="noarchive" in parser.robots_directives,
    )


def contains_credential_marker(body: bytes) -> bool:
    return any(pattern.search(body) is not None for pattern in _SECRET_PATTERNS)


class _BoundedHtmlParser(HTMLParser):
    def __init__(self, *, max_text_chars: int) -> None:
        super().__init__(convert_charrefs=True)
        self.max_text_chars = max_text_chars
        self.text_parts: list[str] = []
        self.title_parts: list[str] = []
        self.title: str | None = None
        self.language: str | None = None
        self.robots_directives: set[str] = set()
        self._ignored_depth = 0
        self._in_title = False
        self._text_chars = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        normalized = tag.casefold()
        attributes = {key.casefold(): value for key, value in attrs}
        if normalized == "html" and attributes.get("lang"):
            self.language = attributes["lang"]
        if normalized in {"script", "style", "noscript", "svg", "template"}:
            self._ignored_depth += 1
            return
        if normalized == "title" and self._ignored_depth == 0:
            self._in_title = True
        if normalized == "meta":
            name = (attributes.get("name") or "").casefold()
            if name in {"robots", "googlebot"}:
                content = (attributes.get("content") or "").casefold()
                self.robots_directives.update(
                    directive.strip()
                    for directive in content.split(",")
                    if directive.strip()
                )

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.casefold()
        if normalized in {"script", "style", "noscript", "svg", "template"}:
            if self._ignored_depth > 0:
                self._ignored_depth -= 1
            return
        if normalized == "title":
            self._in_title = False
            self.title = " ".join(" ".join(self.title_parts).split())[:1_000]

    def handle_data(self, data: str) -> None:
        if self._ignored_depth > 0:
            return
        normalized = " ".join(data.split())
        if not normalized:
            return
        if self._in_title:
            self.title_parts.append(normalized)
        remaining = self.max_text_chars - self._text_chars
        if remaining <= 0:
            return
        bounded = normalized[:remaining]
        self.text_parts.append(bounded)
        self._text_chars += len(bounded)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].casefold()


def _child_text(node: ElementTree.Element, name: str) -> str | None:
    for child in node:
        if _local_name(child.tag) == name and child.text:
            normalized = child.text.strip()
            return normalized or None
    return None


def _parse_optional_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    candidate = value.strip()
    try:
        if len(candidate) == 10:
            return datetime.fromisoformat(candidate).replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from xml.etree import ElementTree

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl

_MAX_FEED_BYTES = 1_000_000
_FORBIDDEN_XML_MARKERS = (b"<!DOCTYPE", b"<!ENTITY")


class PublicFeedParseError(RuntimeError):
    """A configured public RSS/Atom feed could not be parsed safely."""


@dataclass(frozen=True, slots=True)
class FeedEntry:
    url: str
    title: str | None
    published_at: datetime | None


def parse_public_feed(
    body: bytes,
    target: PublicWebTarget,
    *,
    max_entries: int,
) -> tuple[FeedEntry, ...]:
    if not 1 <= max_entries <= target.max_pages:
        raise ValueError("feed entry limit must fit the target page budget")
    if not body or len(body) > _MAX_FEED_BYTES:
        raise PublicFeedParseError("feed body is empty or exceeds the parser byte limit")
    upper = body.upper()
    if any(marker in upper for marker in _FORBIDDEN_XML_MARKERS):
        raise PublicFeedParseError("feed DTD and entities are not allowed")
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as exc:
        raise PublicFeedParseError("invalid feed XML") from exc
    root_name = _local_name(root.tag)
    if root_name == "rss":
        candidates = _rss_entries(root)
    elif root_name == "feed":
        candidates = _atom_entries(root)
    else:
        raise PublicFeedParseError("only RSS 2.0 and Atom feeds are supported")
    return _bounded_entries(candidates, target, max_entries=max_entries)


def _rss_entries(root: ElementTree.Element) -> tuple[FeedEntry, ...]:
    channel = next((node for node in root if _local_name(node.tag) == "channel"), None)
    if channel is None:
        raise PublicFeedParseError("RSS feed is missing channel")
    entries: list[FeedEntry] = []
    for item in channel:
        if _local_name(item.tag) != "item":
            continue
        url = _child_text(item, "link")
        if url is None:
            continue
        entries.append(
            FeedEntry(
                url=url,
                title=_child_text(item, "title"),
                published_at=_parse_time(_child_text(item, "pubDate")),
            )
        )
    return tuple(entries)


def _atom_entries(root: ElementTree.Element) -> tuple[FeedEntry, ...]:
    entries: list[FeedEntry] = []
    for item in root:
        if _local_name(item.tag) != "entry":
            continue
        url = _atom_link(item)
        if url is None:
            continue
        published = _child_text(item, "published") or _child_text(item, "updated")
        entries.append(
            FeedEntry(
                url=url,
                title=_child_text(item, "title"),
                published_at=_parse_time(published),
            )
        )
    return tuple(entries)


def _atom_link(item: ElementTree.Element) -> str | None:
    for child in item:
        if _local_name(child.tag) != "link":
            continue
        rel = (child.attrib.get("rel") or "alternate").casefold()
        href = child.attrib.get("href")
        if rel == "alternate" and href:
            normalized = href.strip()
            if normalized:
                return normalized
    return None


def _bounded_entries(
    candidates: tuple[FeedEntry, ...],
    target: PublicWebTarget,
    *,
    max_entries: int,
) -> tuple[FeedEntry, ...]:
    entries: list[FeedEntry] = []
    seen: set[str] = set()
    for candidate in candidates:
        try:
            canonical = CanonicalUrl(candidate.url).value
        except ValueError:
            continue
        decision = target.crawl_scope.evaluate_target(
            canonical,
            depth=1,
            redirects=0,
            usage=CrawlUsage(pages_fetched=len(entries)),
        )
        if not decision.allowed or canonical in seen:
            continue
        seen.add(canonical)
        entries.append(
            FeedEntry(
                url=canonical,
                title=_bounded_text(candidate.title, 1_000),
                published_at=candidate.published_at,
            )
        )
        if len(entries) == max_entries:
            break
    return tuple(entries)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].casefold()


def _child_text(node: ElementTree.Element, name: str) -> str | None:
    for child in node:
        if _local_name(child.tag) == name and child.text:
            return _bounded_text(child.text, 4_000)
    return None


def _bounded_text(value: str | None, maximum: int) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())[:maximum]
    return normalized or None


def _parse_time(value: str | None) -> datetime | None:
    if value is None:
        return None
    candidate = value.strip()
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        return _parse_rfc822(candidate)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_rfc822(value: str) -> datetime | None:
    from email.utils import parsedate_to_datetime

    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)

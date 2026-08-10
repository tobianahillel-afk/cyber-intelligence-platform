from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.robotparser import RobotFileParser
from uuid import UUID

import httpx
import pytest
from pypdf import PdfWriter

from cip.adapters.sources.public_web.client import (
    PublicWebClient,
    PublicWebPolicyDeniedError,
    PublicWebResponseError,
    RobotsRules,
)
from cip.adapters.sources.public_web.document_parsing import (
    PublicDocumentParseError,
    extract_pdf_text,
    extract_plain_text,
)
from cip.adapters.sources.public_web.feed_parsing import (
    PublicFeedParseError,
    parse_public_feed,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.adapters.sources.public_web.security_txt import (
    SecurityTxtParseError,
    bounded_security_txt_excerpt,
    parse_security_txt,
)

ORG_ID = UUID("00000000-0000-0000-0000-000000000851")
NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
FEED_URL = "https://example.com/public/feed.xml"


def test_feed_rejects_invalid_limits_empty_malformed_and_unknown_xml() -> None:
    target = _target(feed_urls=(FEED_URL,))

    with pytest.raises(ValueError, match="entry limit"):
        parse_public_feed(b"<rss/>", target, max_entries=0)
    with pytest.raises(ValueError, match="entry limit"):
        parse_public_feed(b"<rss/>", target, max_entries=target.max_pages + 1)
    with pytest.raises(PublicFeedParseError, match="empty"):
        parse_public_feed(b"", target, max_entries=1)
    with pytest.raises(PublicFeedParseError, match="invalid feed XML"):
        parse_public_feed(b"<rss>", target, max_entries=1)
    with pytest.raises(PublicFeedParseError, match="RSS 2.0 and Atom"):
        parse_public_feed(b"<catalog/>", target, max_entries=1)


def test_rss_requires_channel_and_skips_missing_or_invalid_links() -> None:
    target = _target(feed_urls=(FEED_URL,))

    with pytest.raises(PublicFeedParseError, match="missing channel"):
        parse_public_feed(b"<rss/>", target, max_entries=5)

    body = b"""<rss version='2.0'><channel>
      <item><title>No link</title></item>
      <item><link>not a valid absolute URL</link></item>
      <item><link>https://example.com/private/nope</link></item>
    </channel></rss>"""
    assert parse_public_feed(body, target, max_entries=5) == ()


def test_feed_deduplicates_caps_entries_and_bounds_titles() -> None:
    target = _target(feed_urls=(FEED_URL,))
    long_title = "x" * 1_500
    body = (
        "<rss version='2.0'><channel>"
        f"<item><title>{long_title}</title><link>https://example.com/public/a</link></item>"
        "<item><link>https://example.com/public/a</link></item>"
        "<item><link>https://example.com/public/b</link></item>"
        "</channel></rss>"
    ).encode()

    entries = parse_public_feed(body, target, max_entries=1)

    assert len(entries) == 1
    assert entries[0].url == "https://example.com/public/a"
    assert entries[0].title == "x" * 1_000


def test_atom_skips_non_alternate_links_and_parses_supported_dates() -> None:
    target = _target(feed_urls=(FEED_URL,))
    body = b"""<feed xmlns='http://www.w3.org/2005/Atom'>
      <entry><link rel='self' href='https://example.com/public/self'/></entry>
      <entry><link rel='alternate'/></entry>
      <entry>
        <link href='https://example.com/public/iso'/>
        <published>2026-08-10T10:30:00Z</published>
      </entry>
      <entry>
        <link href='https://example.com/public/rfc'/>
        <updated>Sun, 10 Aug 2026 11:30:00 +0000</updated>
      </entry>
      <entry>
        <link href='https://example.com/public/bad-date'/>
        <updated>not-a-date</updated>
      </entry>
    </feed>"""

    entries = parse_public_feed(body, target, max_entries=10)

    assert tuple(entry.url for entry in entries) == (
        "https://example.com/public/iso",
        "https://example.com/public/rfc",
        "https://example.com/public/bad-date",
    )
    assert entries[0].published_at == datetime(2026, 8, 10, 10, 30, tzinfo=UTC)
    assert entries[1].published_at is not None
    assert entries[1].published_at.tzinfo is not None
    assert entries[2].published_at is None


def test_feed_normalizes_naive_iso_timestamp_to_utc() -> None:
    target = _target(feed_urls=(FEED_URL,))
    body = b"""<feed xmlns='http://www.w3.org/2005/Atom'><entry>
      <link href='https://example.com/public/naive'/>
      <updated>2026-08-10T10:30:00</updated>
    </entry></feed>"""

    entries = parse_public_feed(body, target, max_entries=5)

    assert entries[0].published_at == datetime(2026, 8, 10, 10, 30, tzinfo=UTC)


def test_security_txt_rejects_empty_invalid_utf8_nul_and_field_overflow() -> None:
    target = _target(discover_security_txt=True)

    with pytest.raises(SecurityTxtParseError, match="empty"):
        parse_security_txt(b"", target)
    with pytest.raises(SecurityTxtParseError, match="UTF-8"):
        parse_security_txt(b"Contact: mailto:security@example.com\n\xff", target)
    with pytest.raises(SecurityTxtParseError, match="NUL"):
        parse_security_txt(b"Contact: mailto:security@example.com\x00", target)

    lines = ["Contact: mailto:security@example.com"]
    lines.extend(f"Policy-{index}: value" for index in range(200))
    with pytest.raises(SecurityTxtParseError, match="too many fields"):
        parse_security_txt("\n".join(lines).encode(), target)


def test_security_txt_rejects_unsupported_contact_and_invalid_canonical() -> None:
    target = _target(discover_security_txt=True)

    with pytest.raises(SecurityTxtParseError, match="valid Contact"):
        parse_security_txt(b"Contact: ftp://example.com/security", target)
    with pytest.raises(SecurityTxtParseError, match="Canonical field is invalid"):
        parse_security_txt(
            b"Contact: mailto:security@example.com\nCanonical: not-a-url",
            target,
        )


def test_security_txt_validates_expires_and_supports_https_contact() -> None:
    target = _target(discover_security_txt=True)

    with pytest.raises(SecurityTxtParseError, match="Expires field is invalid"):
        parse_security_txt(
            b"Contact: https://example.com/public/security\nExpires: tomorrow",
            target,
        )
    with pytest.raises(SecurityTxtParseError, match="requires a timezone"):
        parse_security_txt(
            b"Contact: https://example.com/public/security\nExpires: 2027-01-01T00:00:00",
            target,
        )

    document = parse_security_txt(
        b"# comment\nIgnored line\n"
        b"Contact: https://example.com/public/security\n"
        b"Canonical: https://example.com/.well-known/security.txt\n"
        b"Canonical: https://example.com/.well-known/security.txt\n",
        target,
    )
    assert document.contacts == ("https://example.com/public/security",)
    assert document.canonical_urls == (
        "https://example.com/.well-known/security.txt",
    )
    assert document.expires_at is None
    assert document.preferred_languages == ()


def test_security_txt_language_and_excerpt_bounds_are_deterministic() -> None:
    target = _target(discover_security_txt=True)
    languages = ", ".join(f"x-{index}" for index in range(25))
    body = (
        "Contact: mailto:security@example.com\n"
        "Expires: 2027-01-01T00:00:00Z\n"
        f"Preferred-Languages: {languages}\n"
    ).encode()

    document = parse_security_txt(body, target)
    excerpt = bounded_security_txt_excerpt(document, maximum=80)

    assert len(document.preferred_languages) == 20
    assert document.expires_at == datetime(2027, 1, 1, tzinfo=UTC)
    assert len(excerpt) <= 80
    assert excerpt.startswith("Contact: mailto:security@example.com")
    with pytest.raises(ValueError, match="excerpt bound"):
        bounded_security_txt_excerpt(document, maximum=0)


def test_plain_text_parser_accepts_bounded_text_and_rejects_unsafe_shapes() -> None:
    extracted = extract_plain_text(b"  Security\n  roadmap\t2027  ")
    assert extracted.text == "Security roadmap 2027"
    assert extracted.excerpt == "Security roadmap 2027"
    assert extracted.title is None

    with pytest.raises(PublicDocumentParseError, match="empty"):
        extract_plain_text(b"")
    with pytest.raises(PublicDocumentParseError, match="byte limit"):
        extract_plain_text(b"x" * 1_000_001)
    with pytest.raises(PublicDocumentParseError, match="NUL"):
        extract_plain_text(b"safe\x00unsafe")


def test_pdf_without_title_remains_a_bounded_document() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buffer = _write_pdf(writer)

    extracted = extract_pdf_text(buffer)

    assert extracted.title is None
    assert extracted.text == ""
    assert extracted.excerpt is None


def test_fetch_feed_fails_closed_on_configuration_robots_redirect_and_mime() -> None:
    target = _target(feed_urls=(FEED_URL,))
    allowed = _robots(missing=True)
    denied = _robots(missing=False, lines=("User-agent: *", "Disallow: /public/feed.xml"))

    with httpx.Client(transport=httpx.MockTransport(_ok_feed)) as http_client:
        client = PublicWebClient(http_client)
        with pytest.raises(PublicWebPolicyDeniedError, match="explicitly configured"):
            client.fetch_feed(target, "https://example.com/public/other.xml", allowed)
        with pytest.raises(PublicWebPolicyDeniedError, match="robots.txt denied"):
            client.fetch_feed(target, FEED_URL, denied)

    def redirect(_: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": FEED_URL})

    with httpx.Client(transport=httpx.MockTransport(redirect)) as http_client:
        with pytest.raises(PublicWebResponseError, match="redirects"):
            PublicWebClient(http_client).fetch_feed(target, FEED_URL, allowed)

    def wrong_mime(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html/>")

    with httpx.Client(transport=httpx.MockTransport(wrong_mime)) as http_client:
        with pytest.raises(PublicWebResponseError, match="content type"):
            PublicWebClient(http_client).fetch_feed(target, FEED_URL, allowed)


def test_fetch_feed_rejects_invalid_or_oversized_content_length() -> None:
    target = _target(feed_urls=(FEED_URL,))
    robots = _robots(missing=True)

    def invalid_length(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/rss+xml", "content-length": "invalid"},
            content=b"<rss/>",
        )

    with httpx.Client(transport=httpx.MockTransport(invalid_length)) as http_client:
        with pytest.raises(PublicWebResponseError, match="invalid Content-Length"):
            PublicWebClient(http_client).fetch_feed(target, FEED_URL, robots)

    def oversized_length(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/rss+xml", "content-length": "1000001"},
            content=b"<rss/>",
        )

    with httpx.Client(transport=httpx.MockTransport(oversized_length)) as http_client:
        with pytest.raises(PublicWebResponseError, match="size limit"):
            PublicWebClient(http_client).fetch_feed(target, FEED_URL, robots)


def test_target_rejects_missing_discovery_off_origin_feed_and_unreviewed_enablement() -> None:
    with pytest.raises(ValueError, match="explicit discovery path"):
        _target()
    with pytest.raises(ValueError, match="share the target origin"):
        _target(feed_urls=("https://other.example/public/feed.xml",))
    with pytest.raises(ValueError, match="reviewed authorization"):
        _target(feed_urls=(FEED_URL,), enabled=True)


def test_target_expired_authorization_is_not_executable() -> None:
    target = _target(
        feed_urls=(FEED_URL,),
        enabled=True,
        authorization_reference="review-1",
        authorization_reviewed_at=NOW - timedelta(days=2),
        authorization_expires_at=NOW - timedelta(days=1),
    )

    assert target.executable_at(NOW) is False


def _target(
    *,
    feed_urls: tuple[str, ...] = (),
    discover_security_txt: bool = False,
    enabled: bool = False,
    authorization_reference: str | None = None,
    authorization_reviewed_at: datetime | None = None,
    authorization_expires_at: datetime | None = None,
) -> PublicWebTarget:
    return PublicWebTarget(
        id="public-web-edge-test",
        organization_id=ORG_ID,
        canonical_name="Example",
        base_url="https://example.com",
        sitemap_urls=(),
        feed_urls=feed_urls,
        discover_security_txt=discover_security_txt,
        allowed_path_prefixes=("/public",),
        enabled=enabled,
        authorization_reference=authorization_reference,
        authorization_reviewed_at=authorization_reviewed_at,
        authorization_expires_at=authorization_expires_at,
        max_pages=25,
        max_total_bytes=5_000_000,
        max_resource_bytes=1_000_000,
        max_redirects=2,
    )


def _robots(*, missing: bool, lines: tuple[str, ...] = ()) -> RobotsRules:
    parser = RobotFileParser()
    parser.set_url("https://example.com/robots.txt")
    parser.parse(list(lines))
    return RobotsRules(
        parser=parser,
        source_url="https://example.com/robots.txt",
        missing=missing,
        bytes_fetched=0,
    )


def _ok_feed(_: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        headers={"content-type": "application/rss+xml"},
        content=b"<rss version='2.0'><channel/></rss>",
    )


def _write_pdf(writer: PdfWriter) -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()

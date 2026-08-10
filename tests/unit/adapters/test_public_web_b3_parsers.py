from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID

import pytest
from pypdf import PdfWriter

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
    parse_security_txt,
)

ORG_ID = UUID("00000000-0000-0000-0000-000000000831")
REVIEWED_AT = datetime(2026, 8, 10, 10, 0, tzinfo=UTC)


def test_rss_and_atom_only_emit_in_scope_links() -> None:
    target = _target(feed_urls=("https://example.com/public/feed.xml",))
    rss = b"""<?xml version='1.0'?>
<rss version='2.0'><channel>
  <item><title>Allowed</title><link>https://example.com/public/a</link></item>
  <item><title>Outside path</title><link>https://example.com/private/a</link></item>
  <item><title>Outside host</title><link>https://evil.example/public/a</link></item>
</channel></rss>"""
    atom = b"""<?xml version='1.0'?>
<feed xmlns='http://www.w3.org/2005/Atom'>
  <entry><title>Allowed</title><link rel='alternate' href='https://example.com/public/b'/></entry>
</feed>"""

    rss_entries = parse_public_feed(rss, target, max_entries=10)
    atom_entries = parse_public_feed(atom, target, max_entries=10)

    assert tuple(item.url for item in rss_entries) == ("https://example.com/public/a",)
    assert tuple(item.url for item in atom_entries) == ("https://example.com/public/b",)


def test_feed_rejects_dtd_and_entities() -> None:
    target = _target(feed_urls=("https://example.com/public/feed.xml",))
    body = b"<!DOCTYPE rss [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><rss/>"

    with pytest.raises(PublicFeedParseError, match="DTD and entities"):
        parse_public_feed(body, target, max_entries=10)


def test_security_txt_requires_valid_contact_and_exact_canonical() -> None:
    target = _target(discover_security_txt=True)
    body = b"\n".join(
        (
            b"Contact: mailto:security@example.com",
            b"Canonical: https://example.com/.well-known/security.txt",
            b"Expires: 2027-01-01T00:00:00Z",
            b"Preferred-Languages: fr, en",
        )
    )

    document = parse_security_txt(body, target)

    assert document.contacts == ("mailto:security@example.com",)
    assert document.canonical_urls == (
        "https://example.com/.well-known/security.txt",
    )
    assert document.preferred_languages == ("fr", "en")


def test_security_txt_rejects_wrong_canonical_and_missing_contact() -> None:
    target = _target(discover_security_txt=True)

    with pytest.raises(SecurityTxtParseError, match="Canonical field"):
        parse_security_txt(
            b"Contact: mailto:security@example.com\nCanonical: https://example.com/public/security.txt",
            target,
        )
    with pytest.raises(SecurityTxtParseError, match="Contact"):
        parse_security_txt(b"Expires: 2027-01-01T00:00:00Z", target)


def test_pdf_parser_accepts_bounded_plain_pdf_and_rejects_encrypted_pdf() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.add_metadata({"/Title": "Security architecture"})
    plain_buffer = BytesIO()
    writer.write(plain_buffer)

    extracted = extract_pdf_text(plain_buffer.getvalue())

    assert extracted.title == "Security architecture"
    assert extracted.text == ""

    encrypted_writer = PdfWriter()
    encrypted_writer.add_blank_page(width=100, height=100)
    encrypted_writer.encrypt("secret")
    encrypted_buffer = BytesIO()
    encrypted_writer.write(encrypted_buffer)
    with pytest.raises(PublicDocumentParseError, match="encrypted"):
        extract_pdf_text(encrypted_buffer.getvalue())


def test_document_parser_rejects_malformed_pdf_and_invalid_utf8() -> None:
    with pytest.raises(PublicDocumentParseError):
        extract_pdf_text(b"%PDF-1.7\nnot-a-valid-document")
    with pytest.raises(PublicDocumentParseError, match="UTF-8"):
        extract_plain_text(b"\xff\xfe")


def test_target_can_be_feed_only_and_security_path_is_explicitly_bounded() -> None:
    feed_only = _target(feed_urls=("https://example.com/public/feed.xml",))
    security = _target(discover_security_txt=True)

    assert feed_only.sitemap_urls == ()
    assert feed_only.feed_urls == ("https://example.com/public/feed.xml",)
    assert "/.well-known/security.txt" in security.allowed_path_prefixes
    assert security.security_txt_url == "https://example.com/.well-known/security.txt"


def _target(
    *,
    feed_urls: tuple[str, ...] = (),
    discover_security_txt: bool = False,
) -> PublicWebTarget:
    return PublicWebTarget(
        id="public-web-test",
        organization_id=ORG_ID,
        canonical_name="Example",
        base_url="https://example.com",
        sitemap_urls=() if feed_urls or discover_security_txt else ("https://example.com/sitemap.xml",),
        feed_urls=feed_urls,
        discover_security_txt=discover_security_txt,
        allowed_path_prefixes=("/public",),
        enabled=False,
        authorization_reference=None,
        authorization_reviewed_at=None,
        max_pages=25,
        max_total_bytes=5_000_000,
        max_resource_bytes=1_000_000,
        max_redirects=2,
    )

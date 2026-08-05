from __future__ import annotations

import pytest

from cip.modules.public_footprint.domain import (
    CanonicalUrl,
    CrawlDecisionReason,
    CrawlScope,
    CrawlUsage,
    canonicalize_url,
    same_origin,
)


def test_canonical_url_normalizes_host_port_fragment_and_query() -> None:
    value = canonicalize_url(
        " HTTPS://Exämple.COM:443/public/report?b=2&a=1#section "
    )

    assert value == "https://xn--exmple-cua.com/public/report?a=1&b=2"
    canonical = CanonicalUrl(value)
    assert canonical.host == "xn--exmple-cua.com"
    assert canonical.path == "/public/report"
    assert canonical.origin == "https://xn--exmple-cua.com"


def test_canonical_url_rejects_unsafe_or_unsupported_targets() -> None:
    with pytest.raises(ValueError, match="scheme"):
        canonicalize_url("ftp://example.com/file")
    with pytest.raises(ValueError, match="credentials"):
        canonicalize_url("https://user:secret@example.com/private")
    with pytest.raises(ValueError, match="host"):
        canonicalize_url("https:///missing-host")


def test_same_origin_uses_canonical_origin() -> None:
    assert same_origin("https://EXAMPLE.com:443/a", "https://example.com/b")
    assert not same_origin("http://example.com/a", "https://example.com/a")
    assert not same_origin("https://example.com/a", "https://other.example/a")


def test_crawl_scope_enforces_host_path_depth_redirect_and_page_budgets() -> None:
    scope = CrawlScope(
        allowed_hosts=frozenset({"Example.COM"}),
        allowed_path_prefixes=("/public",),
        max_depth=2,
        max_pages=3,
        max_total_bytes=1_000,
        max_resource_bytes=500,
        max_redirects=1,
    )

    allowed = scope.evaluate_target(
        "https://example.com/public/report",
        depth=2,
        redirects=1,
        usage=CrawlUsage(pages_fetched=2, bytes_fetched=900),
    )
    assert allowed.allowed
    assert allowed.reason is CrawlDecisionReason.ALLOWED

    assert (
        scope.evaluate_target(
            "https://other.example/public/report",
            depth=0,
            redirects=0,
            usage=CrawlUsage(),
        ).reason
        is CrawlDecisionReason.HOST_NOT_ALLOWED
    )
    assert (
        scope.evaluate_target(
            "https://example.com/publicity/report",
            depth=0,
            redirects=0,
            usage=CrawlUsage(),
        ).reason
        is CrawlDecisionReason.PATH_NOT_ALLOWED
    )
    assert (
        scope.evaluate_target(
            "https://example.com/public/report",
            depth=3,
            redirects=0,
            usage=CrawlUsage(),
        ).reason
        is CrawlDecisionReason.DEPTH_EXCEEDED
    )
    assert (
        scope.evaluate_target(
            "https://example.com/public/report",
            depth=0,
            redirects=2,
            usage=CrawlUsage(),
        ).reason
        is CrawlDecisionReason.REDIRECT_LIMIT_EXCEEDED
    )
    assert (
        scope.evaluate_target(
            "https://example.com/public/report",
            depth=0,
            redirects=0,
            usage=CrawlUsage(pages_fetched=3),
        ).reason
        is CrawlDecisionReason.PAGE_BUDGET_EXCEEDED
    )
    assert (
        scope.evaluate_target(
            "https://example.com/public/report",
            depth=0,
            redirects=0,
            usage=CrawlUsage(bytes_fetched=1_000),
        ).reason
        is CrawlDecisionReason.TOTAL_BYTE_BUDGET_EXCEEDED
    )


def test_crawl_scope_enforces_mime_resource_and_total_byte_budgets() -> None:
    scope = CrawlScope(
        allowed_hosts=frozenset({"example.com"}),
        allowed_mime_types=frozenset({"text/html", "application/pdf"}),
        max_total_bytes=1_000,
        max_resource_bytes=500,
    )

    allowed = scope.evaluate_response(
        mime_type="Text/HTML; charset=utf-8",
        resource_bytes=200,
        usage=CrawlUsage(bytes_fetched=700),
    )
    assert allowed.allowed

    assert (
        scope.evaluate_response(
            mime_type="image/png",
            resource_bytes=100,
            usage=CrawlUsage(),
        ).reason
        is CrawlDecisionReason.MIME_NOT_ALLOWED
    )
    assert (
        scope.evaluate_response(
            mime_type="application/pdf",
            resource_bytes=501,
            usage=CrawlUsage(),
        ).reason
        is CrawlDecisionReason.RESOURCE_SIZE_EXCEEDED
    )
    assert (
        scope.evaluate_response(
            mime_type="application/pdf",
            resource_bytes=400,
            usage=CrawlUsage(bytes_fetched=700),
        ).reason
        is CrawlDecisionReason.TOTAL_BYTE_BUDGET_EXCEEDED
    )


def test_crawl_scope_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError, match="bare hostname"):
        CrawlScope(allowed_hosts=frozenset({"https://example.com"}))
    with pytest.raises(ValueError, match="path prefix"):
        CrawlScope(
            allowed_hosts=frozenset({"example.com"}),
            allowed_path_prefixes=("public",),
        )
    with pytest.raises(ValueError, match="cannot exceed"):
        CrawlScope(
            allowed_hosts=frozenset({"example.com"}),
            max_total_bytes=100,
            max_resource_bytes=101,
        )

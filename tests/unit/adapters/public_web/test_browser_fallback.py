from __future__ import annotations

from datetime import UTC, datetime
from urllib.robotparser import RobotFileParser
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.public_web.browser_fallback import (
    BrowserFallbackPolicy,
    FallbackPublicWebClient,
)
from cip.adapters.sources.public_web.client import PublicWebFetchResult, RobotsRules
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_NOW = datetime(2026, 8, 13, 18, tzinfo=UTC)


def test_policy_requires_low_text_html_with_script() -> None:
    policy = BrowserFallbackPolicy(min_static_text_chars=20, max_browser_pages=2)
    scripted = _fetch(b"<html><script></script><p>x</p></html>")
    enough = _fetch(b"<html><p>enough visible static text here</p></html>")

    assert policy.should_render(scripted) is True
    assert policy.should_render(enough) is False
    assert policy.should_render(_fetch(b"<html><p>x</p></html>")) is False
    assert policy.should_render(_fetch(b"{}", mime_type="application/json")) is False
    assert policy.should_render(_fetch(b"<script></script>", status_code=304)) is False


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_static_text_chars": 0},
        {"min_static_text_chars": 100_001},
        {"max_browser_pages": 0},
        {"max_browser_pages": 26},
    ],
)
def test_policy_rejects_unbounded_values(kwargs: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        BrowserFallbackPolicy(**kwargs)


def test_client_uses_browser_and_accounts_static_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    static_body = b"<html><script>boot()</script><div id='app'></div></html>"
    rendered_body = b"<html><body>Rendered application content</body></html>"
    seen_usage: list[CrawlUsage] = []

    class FakeBrowserClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def fetch_page(
            self,
            target: PublicWebTarget,
            url: str,
            robots: RobotsRules,
            *,
            usage: CrawlUsage,
            depth: int = 0,
            etag: str | None = None,
            last_modified: str | None = None,
        ) -> PublicWebFetchResult:
            del target, robots, depth, etag, last_modified
            seen_usage.append(usage)
            return _fetch(rendered_body, url=url)

    import cip.adapters.sources.public_web.browser_client as browser_client_module

    monkeypatch.setattr(browser_client_module, "BrowserPublicWebClient", FakeBrowserClient)
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=static_body,
            request=request,
        )
    )
    target = _target()
    with httpx.Client(transport=transport) as http_client:
        client = FallbackPublicWebClient(
            http_client,
            _entry(SourceType.BROWSER, "browser-source"),
            collected_at=_NOW,
            policy=BrowserFallbackPolicy(
                min_static_text_chars=100,
                max_browser_pages=1,
            ),
        )
        result = client.fetch_page(
            target,
            target.base_url,
            _robots(),
            usage=CrawlUsage(bytes_fetched=7),
        )
        second = client.fetch_page(
            target,
            target.base_url,
            _robots(),
            usage=CrawlUsage(bytes_fetched=len(rendered_body) + 7),
        )

    assert result.body == rendered_body
    assert second.body == static_body
    assert client.fallback_urls == (target.base_url,)
    assert seen_usage[0].bytes_fetched == 7 + len(static_body)


def _fetch(
    body: bytes,
    *,
    mime_type: str = "text/html",
    status_code: int = 200,
    url: str = "https://example.com/",
) -> PublicWebFetchResult:
    return PublicWebFetchResult(
        requested_url=url,
        fetched_url=url,
        body=body,
        mime_type=mime_type,
        etag=None,
        last_modified=None,
        redirects=0,
        status_code=status_code,
    )


def _target() -> PublicWebTarget:
    return PublicWebTarget(
        id="fallback-target",
        source_id="static-source",
        organization_id=uuid4(),
        canonical_name="Fallback Test",
        base_url="https://example.com/",
        seed_urls=("https://example.com/",),
        sitemap_urls=(),
        feed_urls=(),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
        allowed_path_prefixes=("/",),
        enabled=True,
        authorization_reference="static-approval",
        authorization_reviewed_at=_NOW,
        max_link_depth=0,
        max_pages=3,
        max_total_bytes=1_000_000,
        max_resource_bytes=100_000,
        max_redirects=1,
    )


def _robots() -> RobotsRules:
    parser = RobotFileParser()
    parser.set_url("https://example.com/robots.txt")
    parser.parse(["User-agent: *", "Allow: /"])
    return RobotsRules(parser, "https://example.com/robots.txt", False, 0)


def _entry(source_type: SourceType, source_id: str) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        policy=SourcePolicy(
            id=source_id,
            name="Fallback Test",
            base_url="https://example.com/",
            status=SourceStatus.ENABLED,
            source_type=source_type,
            owner="tests",
            licence="Controlled test source",
            allowed_data_categories=frozenset(
                {DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}
            ),
            retention_days=30,
            raw_content_storage=False,
            human_review_required=False,
        ),
        authorization=SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="browser-approval",
            reviewed_at=_NOW,
            approved_hosts=frozenset({"example.com"}),
            approved_path_prefixes=("/",),
            approved_purposes=frozenset({"corporate-public-footprint"}),
            automated_collection_allowed=True,
            raw_storage_allowed=False,
        ),
        economics={"monthly_cost": 0},
    )

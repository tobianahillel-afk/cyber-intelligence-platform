from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.public_web import browser_client
from cip.adapters.sources.public_web.browser_client import BrowserPublicWebClient
from cip.adapters.sources.public_web.browser_runtime import (
    BrowserPolicyDeniedError,
    BrowserRenderError,
    BrowserRenderResult,
)
from cip.adapters.sources.public_web.client import (
    PublicWebFetchResult,
    PublicWebPolicyDeniedError,
    PublicWebResponseError,
    RobotsRules,
)
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

_NOW = datetime(2026, 8, 13, 12, tzinfo=UTC)


def test_browser_client_rejects_robots_denied_page() -> None:
    with httpx.Client(transport=httpx.MockTransport(_unused_transport)) as http_client:
        client = BrowserPublicWebClient(http_client, _entry(), collected_at=_NOW)
        robots = RobotsRules.from_text("User-agent: *\nDisallow: /private\n")

        with pytest.raises(PublicWebPolicyDeniedError, match="robots.txt denied"):
            client.fetch_page(
                _target(),
                "https://example.com/private",
                robots,
                usage=CrawlUsage(),
            )


@pytest.mark.parametrize(
    ("exc", "expected_type", "message"),
    [
        (BrowserPolicyDeniedError("scope denied"), PublicWebPolicyDeniedError, "scope denied"),
        (BrowserRenderError("render failed"), PublicWebResponseError, "render failed"),
    ],
)
def test_browser_client_maps_runtime_errors(
    monkeypatch: pytest.MonkeyPatch,
    exc: Exception,
    expected_type: type[Exception],
    message: str,
) -> None:
    def fail_render(*_args: object, **_kwargs: object) -> BrowserRenderResult:
        raise exc

    monkeypatch.setattr(browser_client, "render_public_web_page", fail_render)
    with httpx.Client(transport=httpx.MockTransport(_unused_transport)) as http_client:
        client = BrowserPublicWebClient(http_client, _entry(), collected_at=_NOW)
        with pytest.raises(expected_type, match=message):
            client.fetch_page(
                _target(),
                "https://example.com/app",
                RobotsRules.allow_all(),
                usage=CrawlUsage(),
            )


def test_browser_client_authorization_callback_uses_source_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorized: list[tuple[str, datetime]] = []

    def fake_authorize(_entry: SourceRegistryEntry, url: str, *, now: datetime) -> None:
        authorized.append((url, now))

    def fake_render(
        _target: PublicWebTarget,
        url: str,
        *,
        usage: CrawlUsage,
        depth: int,
        authorize_url,
        limits,
    ) -> BrowserRenderResult:
        del usage, depth, limits
        authorize_url(url)
        return BrowserRenderResult(
            fetch_result=PublicWebFetchResult(
                requested_url=url,
                fetched_url=url,
                body=b"<html><body>Rendered</body></html>",
                mime_type="text/html",
                etag=None,
                last_modified=None,
                redirects=0,
            ),
            requests_seen=1,
            requests_blocked=0,
        )

    monkeypatch.setattr(browser_client, "authorize_public_web_url", fake_authorize)
    monkeypatch.setattr(browser_client, "render_public_web_page", fake_render)
    with httpx.Client(transport=httpx.MockTransport(_unused_transport)) as http_client:
        client = BrowserPublicWebClient(http_client, _entry(), collected_at=_NOW)
        result = client.fetch_page(
            _target(),
            "https://example.com/app",
            RobotsRules.allow_all(),
            usage=CrawlUsage(),
            etag='"ignored"',
            last_modified="ignored",
        )

    assert result.body == b"<html><body>Rendered</body></html>"
    assert authorized == [("https://example.com/app", _NOW)]


def _unused_transport(request: httpx.Request) -> httpx.Response:
    return httpx.Response(500, request=request)


def _target() -> PublicWebTarget:
    return PublicWebTarget(
        id="browser-client-test",
        organization_id=uuid4(),
        canonical_name="Browser Client Test",
        base_url="https://example.com/",
        seed_urls=("https://example.com/app",),
        sitemap_urls=(),
        feed_urls=(),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
        allowed_path_prefixes=("/",),
        enabled=True,
        authorization_reference="browser-client-test-approval",
        authorization_reviewed_at=_NOW,
        max_link_depth=0,
        max_pages=1,
        max_total_bytes=20_000,
        max_resource_bytes=10_000,
        max_redirects=2,
    )


def _entry() -> SourceRegistryEntry:
    return SourceRegistryEntry(
        policy=SourcePolicy(
            id="browser-client-test",
            name="Browser Client Test",
            base_url="https://example.com/",
            status=SourceStatus.ENABLED,
            source_type=SourceType.BROWSER,
            owner="tests",
            licence="Controlled browser client test source",
            allowed_data_categories=frozenset(
                {
                    DataCategory.OFFICIAL_DOCUMENT_DISCOVERY,
                    DataCategory.TECHNOLOGY_OBSERVATION,
                }
            ),
            retention_days=30,
            raw_content_storage=False,
            human_review_required=False,
        ),
        authorization=SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="browser-client-test-approval",
            reviewed_at=_NOW,
            approved_hosts=frozenset({"example.com"}),
            approved_path_prefixes=("/",),
            approved_purposes=frozenset({"corporate-public-footprint"}),
            automated_collection_allowed=True,
            raw_storage_allowed=False,
        ),
        economics={"monthly_cost": 0},
    )

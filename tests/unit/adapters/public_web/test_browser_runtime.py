from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.public_web import browser_client, browser_runtime
from cip.adapters.sources.public_web.browser_client import BrowserPublicWebClient
from cip.adapters.sources.public_web.browser_runtime import (
    BrowserPolicyDeniedError,
    BrowserRenderError,
    BrowserRenderLimits,
    BrowserRenderResult,
    render_public_web_page,
)
from cip.adapters.sources.public_web.client import PublicWebFetchResult
from cip.adapters.sources.public_web.collector import collect_public_web_target
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


class _FakePlaywrightError(Exception):
    pass


class _FakeRequest:
    def __init__(
        self,
        url: str,
        *,
        resource_type: str,
        navigation: bool,
        frame: object,
    ) -> None:
        self.url = url
        self.resource_type = resource_type
        self.frame = frame
        self._navigation = navigation

    def is_navigation_request(self) -> bool:
        return self._navigation


class _FakeRoute:
    def __init__(self, request: _FakeRequest) -> None:
        self.request = request
        self.aborted = False
        self.continued = False

    def abort(self) -> None:
        self.aborted = True

    def continue_(self) -> None:
        self.continued = True


class _FakeResponse:
    def __init__(self, *, status: int, content_type: str) -> None:
        self.status = status
        self._content_type = content_type

    def header_value(self, name: str) -> str | None:
        return self._content_type if name.casefold() == "content-type" else None


class _FakePage:
    def __init__(
        self,
        *,
        final_url: str,
        content: str,
        status: int = 200,
        content_type: str = "text/html; charset=utf-8",
        extras: tuple[tuple[str, str, bool], ...] = (),
        fail_navigation: bool = False,
    ) -> None:
        self.url = final_url
        self.main_frame = object()
        self._content = content
        self._status = status
        self._content_type = content_type
        self._extras = extras
        self._fail_navigation = fail_navigation
        self._route_handler = None
        self.navigation_timeout = None
        self.settle_waits: list[int] = []
        self.routes: list[_FakeRoute] = []

    def set_default_navigation_timeout(self, value: int) -> None:
        self.navigation_timeout = value

    def route(self, _pattern: str, handler: object) -> None:
        self._route_handler = handler

    def goto(self, url: str, **_kwargs: object) -> _FakeResponse:
        if self._fail_navigation:
            raise _FakePlaywrightError("navigation failed")
        assert callable(self._route_handler)
        main = _FakeRoute(
            _FakeRequest(
                url,
                resource_type="document",
                navigation=True,
                frame=self.main_frame,
            )
        )
        self._route_handler(main)
        self.routes.append(main)
        if main.aborted:
            raise _FakePlaywrightError("main navigation blocked")
        for extra_url, resource_type, navigation in self._extras:
            route = _FakeRoute(
                _FakeRequest(
                    extra_url,
                    resource_type=resource_type,
                    navigation=navigation,
                    frame=self.main_frame,
                )
            )
            self._route_handler(route)
            self.routes.append(route)
        return _FakeResponse(status=self._status, content_type=self._content_type)

    def wait_for_timeout(self, value: int) -> None:
        self.settle_waits.append(value)

    def content(self) -> str:
        return self._content


class _FakeContext:
    def __init__(self, page: _FakePage) -> None:
        self.page = page
        self.closed = False

    def new_page(self) -> _FakePage:
        return self.page

    def close(self) -> None:
        self.closed = True


class _FakeBrowser:
    def __init__(self, page: _FakePage) -> None:
        self.context = _FakeContext(page)
        self.context_kwargs: dict[str, object] = {}
        self.closed = False

    def new_context(self, **kwargs: object) -> _FakeContext:
        self.context_kwargs = kwargs
        return self.context

    def close(self) -> None:
        self.closed = True


class _FakeChromium:
    def __init__(self, browser: _FakeBrowser) -> None:
        self.browser = browser
        self.launch_kwargs: dict[str, object] = {}

    def launch(self, **kwargs: object) -> _FakeBrowser:
        self.launch_kwargs = kwargs
        return self.browser


class _FakeManager:
    def __init__(self, chromium: _FakeChromium) -> None:
        self.chromium = chromium

    def __enter__(self) -> _FakeManager:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_browser_render_uses_sandbox_and_isolated_context(monkeypatch: pytest.MonkeyPatch) -> None:
    page = _FakePage(
        final_url="https://example.com/app",
        content="<html><body>Kubernetes</body></html>",
    )
    browser = _install_fake_playwright(monkeypatch, page)
    authorized: list[str] = []

    rendered = render_public_web_page(
        _target(),
        "https://example.com/app",
        usage=CrawlUsage(),
        depth=0,
        authorize_url=authorized.append,
    )

    assert rendered.fetch_result.body.endswith(b"</html>")
    assert rendered.fetch_result.etag is None
    assert rendered.requests_seen == 1
    assert browser.chromium.launch_kwargs == {"headless": True, "chromium_sandbox": True}
    assert browser.chromium.browser.context_kwargs == {
        "accept_downloads": False,
        "bypass_csp": False,
        "ignore_https_errors": False,
        "java_script_enabled": True,
        "service_workers": "block",
    }
    assert browser.chromium.browser.context.closed
    assert browser.chromium.browser.closed
    assert authorized == [
        "https://example.com/app",
        "https://example.com/app",
        "https://example.com/app",
    ]


def test_browser_blocks_cross_origin_subresource_without_leaving_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = _FakePage(
        final_url="https://example.com/app",
        content="<html><body>Rendered</body></html>",
        extras=(("https://tracker.invalid/script.js", "script", False),),
    )
    _install_fake_playwright(monkeypatch, page)

    rendered = render_public_web_page(
        _target(),
        "https://example.com/app",
        usage=CrawlUsage(),
        depth=0,
        authorize_url=lambda _url: None,
    )

    assert rendered.requests_seen == 2
    assert rendered.requests_blocked == 1
    assert page.routes[0].continued
    assert page.routes[1].aborted


def test_browser_request_and_redirect_budgets_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = _FakePage(
        final_url="https://example.com/app",
        content="<html></html>",
        extras=(("https://example.com/app.js", "script", False),),
    )
    _install_fake_playwright(monkeypatch, page)
    with pytest.raises(BrowserPolicyDeniedError, match="browser_request_budget_exceeded"):
        render_public_web_page(
            _target(),
            "https://example.com/app",
            usage=CrawlUsage(),
            depth=0,
            authorize_url=lambda _url: None,
            limits=BrowserRenderLimits(max_requests=1),
        )

    redirect_page = _FakePage(
        final_url="https://example.com/app",
        content="<html></html>",
        extras=(("https://example.com/app", "document", True),),
    )
    _install_fake_playwright(monkeypatch, redirect_page)
    with pytest.raises(BrowserPolicyDeniedError, match="redirect_limit_exceeded"):
        render_public_web_page(
            _target(max_redirects=0),
            "https://example.com/app",
            usage=CrawlUsage(),
            depth=0,
            authorize_url=lambda _url: None,
        )


def test_browser_rejects_bad_origin_policy_mime_status_and_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(BrowserPolicyDeniedError, match="origin_not_allowed"):
        render_public_web_page(
            _target(),
            "https://other.example/app",
            usage=CrawlUsage(),
            depth=0,
            authorize_url=lambda _url: None,
        )
    with pytest.raises(BrowserPolicyDeniedError, match="source_policy_denied"):
        render_public_web_page(
            _target(),
            "https://example.com/app",
            usage=CrawlUsage(),
            depth=0,
            authorize_url=_deny,
        )

    non_html = _FakePage(
        final_url="https://example.com/app",
        content="{}",
        content_type="application/json",
    )
    _install_fake_playwright(monkeypatch, non_html)
    with pytest.raises(BrowserRenderError, match="browser_response_not_html"):
        _render_with_noop_policy(_target(), "https://example.com/app")

    failed = _FakePage(
        final_url="https://example.com/app",
        content="<html></html>",
        status=503,
    )
    _install_fake_playwright(monkeypatch, failed)
    with pytest.raises(BrowserRenderError, match="browser_http_503"):
        _render_with_noop_policy(_target(), "https://example.com/app")

    oversized = _FakePage(
        final_url="https://example.com/app",
        content="<html>" + ("x" * 200) + "</html>",
    )
    _install_fake_playwright(monkeypatch, oversized)
    with pytest.raises(BrowserPolicyDeniedError, match="resource_size_exceeded"):
        _render_with_noop_policy(_target(max_resource_bytes=100), "https://example.com/app")


def test_browser_wraps_playwright_navigation_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    page = _FakePage(
        final_url="https://example.com/app",
        content="<html></html>",
        fail_navigation=True,
    )
    _install_fake_playwright(monkeypatch, page)

    with pytest.raises(BrowserRenderError, match="browser_navigation_failed"):
        _render_with_noop_policy(_target(), "https://example.com/app")


def test_browser_client_reuses_canonical_collector_and_adapter_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 8, 13, 12, tzinfo=UTC)
    target = _target()
    entry = _entry(target, now)
    rendered_html = b"<html><body>Kubernetes Zero Trust</body></html>"

    def fake_render(*_args: object, **_kwargs: object) -> BrowserRenderResult:
        return BrowserRenderResult(
            fetch_result=PublicWebFetchResult(
                requested_url="https://example.com/app",
                fetched_url="https://example.com/app",
                body=rendered_html,
                mime_type="text/html",
                etag=None,
                last_modified=None,
                redirects=0,
            ),
            requests_seen=1,
            requests_blocked=0,
        )

    monkeypatch.setattr(browser_client, "render_public_web_page", fake_render)

    def transport(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/robots.txt"
        return httpx.Response(404, request=request)

    with httpx.Client(transport=httpx.MockTransport(transport)) as http_client:
        batch = collect_public_web_target(
            BrowserPublicWebClient(http_client, entry, collected_at=now),
            entry,
            target,
            collection_job_id=uuid4(),
            collected_at=now,
            retention_until=now + timedelta(days=30),
            adapter_id="public-web-browser",
        )

    assert len(batch.observations) == 1
    assert batch.observations[0].adapter_id == "public-web-browser"
    assert batch.projections[0].version.extracted_text_hash_sha256 is not None
    assert len(batch.projections[0].claims) == 2


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_requests": 0}, "max_requests"),
        ({"navigation_timeout_ms": 99}, "navigation_timeout_ms"),
        ({"settle_timeout_ms": 5_001}, "settle_timeout_ms"),
    ],
)
def test_browser_render_limits_reject_invalid_values(
    kwargs: dict[str, int],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        BrowserRenderLimits(**kwargs)


def _install_fake_playwright(
    monkeypatch: pytest.MonkeyPatch,
    page: _FakePage,
) -> _FakeManager:
    manager = _FakeManager(_FakeChromium(_FakeBrowser(page)))
    monkeypatch.setattr(browser_runtime, "sync_playwright", lambda: manager)
    monkeypatch.setattr(browser_runtime, "PlaywrightError", _FakePlaywrightError)
    return manager


def _render_with_noop_policy(target: PublicWebTarget, url: str) -> BrowserRenderResult:
    return render_public_web_page(
        target,
        url,
        usage=CrawlUsage(),
        depth=0,
        authorize_url=lambda _url: None,
    )


def _target(
    *,
    max_redirects: int = 2,
    max_resource_bytes: int = 10_000,
) -> PublicWebTarget:
    return PublicWebTarget(
        id="browser-test",
        organization_id=uuid4(),
        canonical_name="Browser Test",
        base_url="https://example.com/",
        seed_urls=("https://example.com/app",),
        sitemap_urls=(),
        feed_urls=(),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
        allowed_path_prefixes=("/",),
        enabled=True,
        authorization_reference="browser-test-approval",
        authorization_reviewed_at=datetime(2026, 8, 13, 12, tzinfo=UTC),
        max_link_depth=0,
        max_pages=2,
        max_total_bytes=20_000,
        max_resource_bytes=max_resource_bytes,
        max_redirects=max_redirects,
    )


def _entry(target: PublicWebTarget, now: datetime) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        policy=SourcePolicy(
            id=target.id,
            name="Browser Test",
            base_url=target.base_url,
            status=SourceStatus.ENABLED,
            source_type=SourceType.BROWSER,
            owner="tests",
            licence="Controlled test browser source",
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
            document_reference="browser-test-approval",
            reviewed_at=now,
            approved_hosts=frozenset({target.host}),
            approved_path_prefixes=("/",),
            approved_purposes=frozenset({"corporate-public-footprint"}),
            automated_collection_allowed=True,
            raw_storage_allowed=False,
        ),
        economics={"monthly_cost": 0},
    )


def _deny(_url: str) -> None:
    raise RuntimeError("denied")

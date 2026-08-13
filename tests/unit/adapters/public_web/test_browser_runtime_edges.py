from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from cip.adapters.sources.public_web.browser_runtime import (
    BrowserPolicyDeniedError,
    BrowserRenderError,
    BrowserRenderLimits,
    _authorized_request_url,
    _BrowserState,
    _handle_route,
    _render_result,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.scope import CrawlUsage

_NOW = datetime(2026, 8, 13, 12, tzinfo=UTC)


class _Page:
    url = "https://example.com/app"
    main_frame = object()

    def wait_for_timeout(self, _value: int) -> None:
        return None

    def content(self) -> str:
        return "<html></html>"


class _Request:
    def __init__(self, *, url: str, resource_type: str, navigation: bool = False) -> None:
        self.url = url
        self.resource_type = resource_type
        self.frame = _Page.main_frame
        self._navigation = navigation

    def is_navigation_request(self) -> bool:
        return self._navigation


class _Route:
    def __init__(self, request: _Request) -> None:
        self.request = request
        self.aborted = False
        self.continued = False

    def abort(self) -> None:
        self.aborted = True

    def continue_(self) -> None:
        self.continued = True


def test_render_result_rejects_missing_navigation_response() -> None:
    with pytest.raises(BrowserRenderError, match="no_response"):
        _render_result(
            _Page(),
            None,
            _target(),
            CrawlUsage(),
            0,
            lambda _url: None,
            BrowserRenderLimits(),
            _BrowserState(),
            "https://example.com/app",
        )


def test_route_blocks_media_without_network_policy_expansion() -> None:
    route = _Route(_Request(url="https://cdn.invalid/logo.png", resource_type="image"))
    state = _BrowserState()

    _handle_route(
        route,
        _Page(),
        _target(),
        CrawlUsage(),
        0,
        lambda _url: pytest.fail("blocked media must not reach source policy"),
        BrowserRenderLimits(),
        state,
    )

    assert route.aborted
    assert not route.continued
    assert state.requests_seen == 1
    assert state.requests_blocked == 1
    assert state.denial is None


def test_authorized_request_rejects_invalid_url_and_out_of_scope_path() -> None:
    with pytest.raises(BrowserPolicyDeniedError, match="url_invalid"):
        _authorized_request_url(
            _target(),
            "javascript:alert(1)",
            usage=CrawlUsage(),
            depth=0,
            authorize_url=lambda _url: None,
        )

    with pytest.raises(BrowserPolicyDeniedError, match="path_not_allowed"):
        _authorized_request_url(
            _target(allowed_path_prefixes=("/allowed",)),
            "https://example.com/private",
            usage=CrawlUsage(),
            depth=0,
            authorize_url=lambda _url: None,
        )


def test_main_navigation_policy_denial_is_recorded_and_aborted() -> None:
    route = _Route(
        _Request(
            url="https://other.example/app",
            resource_type="document",
            navigation=True,
        )
    )
    state = _BrowserState()

    _handle_route(
        route,
        _Page(),
        _target(),
        CrawlUsage(),
        0,
        lambda _url: None,
        BrowserRenderLimits(),
        state,
    )

    assert route.aborted
    assert state.requests_blocked == 1
    assert state.denial == "browser_request_origin_not_allowed"


def _target(
    *,
    allowed_path_prefixes: tuple[str, ...] = ("/",),
) -> PublicWebTarget:
    return PublicWebTarget(
        id="browser-edge-test",
        organization_id=uuid4(),
        canonical_name="Browser Edge Test",
        base_url="https://example.com/",
        seed_urls=("https://example.com/app",),
        sitemap_urls=(),
        feed_urls=(),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
        allowed_path_prefixes=allowed_path_prefixes,
        enabled=True,
        authorization_reference="browser-edge-test-approval",
        authorization_reviewed_at=_NOW,
        max_link_depth=0,
        max_pages=1,
        max_total_bytes=20_000,
        max_resource_bytes=10_000,
        max_redirects=2,
    )

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, Request, Response, Route, sync_playwright

from cip.adapters.sources.public_web.client import PublicWebFetchResult
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl, same_origin

AuthorizeUrl = Callable[[str], None]
_BLOCKED_RESOURCE_TYPES = frozenset({"font", "image", "media"})


class BrowserRenderError(RuntimeError):
    """A bounded browser render could not safely produce a representation."""


class BrowserPolicyDeniedError(BrowserRenderError):
    """Browser navigation or a required request violated the governed scope."""


@dataclass(frozen=True, slots=True)
class BrowserRenderLimits:
    max_requests: int = 64
    navigation_timeout_ms: int = 15_000
    settle_timeout_ms: int = 250

    def __post_init__(self) -> None:
        if not 1 <= self.max_requests <= 1_000:
            raise ValueError("max_requests must be between 1 and 1000")
        if not 100 <= self.navigation_timeout_ms <= 120_000:
            raise ValueError("navigation_timeout_ms must be between 100 and 120000")
        if not 0 <= self.settle_timeout_ms <= 5_000:
            raise ValueError("settle_timeout_ms must be between 0 and 5000")


@dataclass(frozen=True, slots=True)
class BrowserRenderResult:
    fetch_result: PublicWebFetchResult
    requests_seen: int
    requests_blocked: int


@dataclass(slots=True)
class _BrowserState:
    requests_seen: int = 0
    requests_blocked: int = 0
    main_navigations: int = 0
    denial: str | None = None


def render_public_web_page(
    target: PublicWebTarget,
    url: str,
    *,
    usage: CrawlUsage,
    depth: int,
    authorize_url: AuthorizeUrl,
    limits: BrowserRenderLimits | None = None,
) -> BrowserRenderResult:
    bounded = limits or BrowserRenderLimits()
    requested = _authorized_request_url(
        target,
        url,
        usage=usage,
        depth=depth,
        authorize_url=authorize_url,
    )
    state = _BrowserState()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, chromium_sandbox=True)
            try:
                context = browser.new_context(
                    accept_downloads=False,
                    bypass_csp=False,
                    ignore_https_errors=False,
                    java_script_enabled=True,
                    service_workers="block",
                )
                try:
                    page = context.new_page()
                    page.set_default_navigation_timeout(bounded.navigation_timeout_ms)
                    page.route(
                        "**/*",
                        lambda route: _handle_route(
                            route,
                            page,
                            target,
                            usage,
                            depth,
                            authorize_url,
                            bounded,
                            state,
                        ),
                    )
                    response = page.goto(
                        requested,
                        wait_until="load",
                        timeout=bounded.navigation_timeout_ms,
                    )
                    return _render_result(
                        page,
                        response,
                        target,
                        usage,
                        depth,
                        authorize_url,
                        bounded,
                        state,
                        requested,
                    )
                finally:
                    context.close()
            finally:
                browser.close()
    except BrowserRenderError:
        raise
    except PlaywrightError as exc:
        if state.denial is not None:
            raise BrowserPolicyDeniedError(state.denial) from exc
        raise BrowserRenderError("browser_navigation_failed") from exc


def _render_result(
    page: Page,
    response: Response | None,
    target: PublicWebTarget,
    usage: CrawlUsage,
    depth: int,
    authorize_url: AuthorizeUrl,
    limits: BrowserRenderLimits,
    state: _BrowserState,
    requested: str,
) -> BrowserRenderResult:
    if state.denial is not None:
        raise BrowserPolicyDeniedError(state.denial)
    if response is None:
        raise BrowserRenderError("browser_navigation_returned_no_response")
    if response.status >= 400:
        raise BrowserRenderError(f"browser_http_{response.status}")
    content_type = (response.header_value("content-type") or "").split(";", 1)[0]
    if content_type.strip().casefold() != "text/html":
        raise BrowserRenderError("browser_response_not_html")
    if limits.settle_timeout_ms:
        page.wait_for_timeout(limits.settle_timeout_ms)
    final_url = _authorized_request_url(
        target,
        page.url,
        usage=usage,
        depth=depth,
        authorize_url=authorize_url,
    )
    body = page.content().encode("utf-8")
    decision = target.crawl_scope.evaluate_response(
        mime_type="text/html",
        resource_bytes=len(body),
        usage=usage,
    )
    if not decision.allowed:
        raise BrowserPolicyDeniedError(decision.reason.value)
    redirects = max(0, state.main_navigations - 1)
    if redirects > target.max_redirects:
        raise BrowserPolicyDeniedError("redirect_limit_exceeded")
    return BrowserRenderResult(
        fetch_result=PublicWebFetchResult(
            requested_url=requested,
            fetched_url=final_url,
            body=body,
            mime_type="text/html",
            etag=None,
            last_modified=None,
            redirects=redirects,
            status_code=response.status,
        ),
        requests_seen=state.requests_seen,
        requests_blocked=state.requests_blocked,
    )


def _handle_route(
    route: Route,
    page: Page,
    target: PublicWebTarget,
    usage: CrawlUsage,
    depth: int,
    authorize_url: AuthorizeUrl,
    limits: BrowserRenderLimits,
    state: _BrowserState,
) -> None:
    request = route.request
    state.requests_seen += 1
    main_navigation = _is_main_navigation(request, page)
    if main_navigation:
        state.main_navigations += 1
    if state.requests_seen > limits.max_requests:
        state.denial = "browser_request_budget_exceeded"
        state.requests_blocked += 1
        route.abort()
        return
    if request.resource_type in _BLOCKED_RESOURCE_TYPES:
        state.requests_blocked += 1
        route.abort()
        return
    try:
        _authorized_request_url(
            target,
            request.url,
            usage=usage,
            depth=depth,
            authorize_url=authorize_url,
        )
    except BrowserPolicyDeniedError as exc:
        state.requests_blocked += 1
        if main_navigation:
            state.denial = str(exc)
        route.abort()
        return
    if state.main_navigations > target.max_redirects + 1:
        state.denial = "redirect_limit_exceeded"
        state.requests_blocked += 1
        route.abort()
        return
    route.continue_()


def _authorized_request_url(
    target: PublicWebTarget,
    raw_url: str,
    *,
    usage: CrawlUsage,
    depth: int,
    authorize_url: AuthorizeUrl,
) -> str:
    try:
        canonical = CanonicalUrl(raw_url)
    except ValueError as exc:
        raise BrowserPolicyDeniedError("browser_request_url_invalid") from exc
    if not same_origin(target.base_url, canonical):
        raise BrowserPolicyDeniedError("browser_request_origin_not_allowed")
    decision = target.crawl_scope.evaluate_target(
        canonical,
        depth=depth,
        redirects=0,
        usage=usage,
    )
    if not decision.allowed:
        raise BrowserPolicyDeniedError(decision.reason.value)
    try:
        authorize_url(canonical.value)
    except RuntimeError as exc:
        raise BrowserPolicyDeniedError("browser_source_policy_denied") from exc
    return canonical.value


def _is_main_navigation(request: Request, page: Page) -> bool:
    return request.is_navigation_request() and request.frame == page.main_frame

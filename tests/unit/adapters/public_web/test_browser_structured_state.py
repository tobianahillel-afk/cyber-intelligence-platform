from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

from playwright.sync_api import Page, Response

from cip.adapters.sources.public_web.browser_runtime import (
    _BrowserState,
    _capture_response,
    _capture_script_state,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain import PublicStructuredStateKind
from cip.modules.public_footprint.domain.scope import CrawlUsage

_NOW = datetime(2026, 8, 14, 13, tzinfo=UTC)


class _Response:
    def __init__(
        self,
        *,
        url: str,
        body: bytes,
        content_type: str = "application/json",
        content_length: str | None = None,
        status: int = 200,
    ) -> None:
        self.url = url
        self.status = status
        self._body = body
        self._content_type = content_type
        self._content_length = content_length
        self.body_called = False

    def header_value(self, name: str) -> str | None:
        if name.casefold() == "content-type":
            return self._content_type
        if name.casefold() == "content-length":
            return self._content_length
        return None

    def body(self) -> bytes:
        self.body_called = True
        return self._body


class _Page:
    def __init__(self, raw: object) -> None:
        self.raw = raw
        self.expressions: list[str] = []

    def evaluate(self, expression: str) -> object:
        self.expressions.append(expression)
        return self.raw


def test_browser_captures_authorized_same_origin_json_and_sanitizes() -> None:
    state = _BrowserState()
    response = _Response(
        url="https://example.com/api/state",
        body=json.dumps(
            {
                "vendor": "Splunk",
                "accessToken": "drop-me",
                "nested": {"sessionId": "drop-me-too", "region": "eu"},
            }
        ).encode(),
    )
    authorized: list[str] = []

    _capture_response(
        cast(Response, response),
        _target(),
        CrawlUsage(),
        0,
        authorized.append,
        state,
    )

    assert response.body_called
    assert authorized == ["https://example.com/api/state"]
    assert len(state.captured_states) == 1
    captured = state.captured_states[0]
    assert captured.kind is PublicStructuredStateKind.NETWORK_JSON
    assert json.loads(captured.payload_json) == {
        "nested": {"region": "eu"},
        "vendor": "Splunk",
    }


def test_browser_does_not_read_off_origin_non_json_or_oversized_response_body() -> None:
    target = _target()
    state = _BrowserState()
    responses = (
        _Response(
            url="https://other.example/api/state",
            body=b'{"value":"off-origin"}',
        ),
        _Response(
            url="https://example.com/api/text",
            body=b'{"value":"wrong mime"}',
            content_type="text/plain",
        ),
        _Response(
            url="https://example.com/api/large",
            body=b'{"value":"large"}',
            content_length=str(state.structured.limits.max_response_bytes + 1),
        ),
    )

    for response in responses:
        _capture_response(
            cast(Response, response),
            target,
            CrawlUsage(),
            0,
            lambda _url: None,
            state,
        )

    assert state.captured_states == []
    assert all(not response.body_called for response in responses)


def test_browser_fixed_script_extractor_only_promotes_reviewed_sanitized_state() -> None:
    state = _BrowserState()
    page = _Page(
        {
            "__INITIAL_STATE__": {
                "company": "Example",
                "password": "drop-me",
            },
            "unreviewed": {"should": "not-be-seen"},
        }
    )

    captured = _capture_script_state(cast(Page, page), state)

    assert len(page.expressions) == 1
    assert len(captured) == 1
    assert captured[0].kind is PublicStructuredStateKind.SCRIPT_STATE
    assert captured[0].source_locator == "window.__INITIAL_STATE__"
    assert json.loads(captured[0].payload_json) == {"company": "Example"}


def _target() -> PublicWebTarget:
    return PublicWebTarget(
        id="browser-structured-state-test",
        organization_id=uuid4(),
        canonical_name="Example",
        base_url="https://example.com/",
        seed_urls=("https://example.com/app",),
        sitemap_urls=(),
        feed_urls=(),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
        allowed_path_prefixes=("/",),
        enabled=True,
        authorization_reference="approval:test",
        authorization_reviewed_at=_NOW - timedelta(days=1),
        authorization_expires_at=_NOW + timedelta(days=30),
        max_link_depth=0,
        max_pages=2,
        max_total_bytes=100_000,
        max_resource_bytes=50_000,
        max_redirects=1,
    )

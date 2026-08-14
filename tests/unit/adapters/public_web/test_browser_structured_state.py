from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

from playwright.sync_api import Page, Request, Response

from cip.adapters.sources.public_web.browser_structured_state import (
    capture_finished_request,
    capture_reviewed_script_state,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.adapters.sources.public_web.structured_state_capture import (
    StructuredStateCapture,
    StructuredStateCaptureLimits,
)
from cip.modules.public_footprint.domain import PublicStructuredStateKind

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
        self.body_bytes = body
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
        return self.body_bytes


class _Request:
    def __init__(self, response: _Response, body_size: int) -> None:
        self._response = response
        self._body_size = body_size

    def response(self) -> Response:
        return cast(Response, self._response)

    def sizes(self) -> dict[str, int]:
        return {
            "requestBodySize": 0,
            "requestHeadersSize": 100,
            "responseBodySize": self._body_size,
            "responseHeadersSize": 100,
        }


class _BrokenRequest(_Request):
    def sizes(self) -> dict[str, int]:
        return {}


class _Page:
    def __init__(self, raw: object) -> None:
        self.raw = raw
        self.expressions: list[str] = []
        self.arguments: list[object] = []

    def evaluate(self, expression: str, argument: object = None) -> object:
        self.expressions.append(expression)
        self.arguments.append(argument)
        return self.raw


def test_browser_captures_authorized_finished_same_origin_json_and_sanitizes() -> None:
    capture = StructuredStateCapture(StructuredStateCaptureLimits())
    states = []
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

    capture_finished_request(
        cast(Request, _Request(response, len(response.body_bytes))),
        capture=capture,
        authorize_url=lambda url: _record_authorized(url, authorized),
        sink=states.append,
    )

    assert response.body_called
    assert authorized == ["https://example.com/api/state"]
    assert len(states) == 1
    captured = states[0]
    assert captured.kind is PublicStructuredStateKind.NETWORK_JSON
    assert json.loads(captured.payload_json) == {
        "nested": {"region": "eu"},
        "vendor": "Splunk",
    }


def test_browser_does_not_read_off_origin_non_json_or_oversized_response_body() -> None:
    capture = StructuredStateCapture(StructuredStateCaptureLimits())
    states = []
    responses_and_sizes = (
        (
            _Response(
                url="https://other.example/api/state",
                body=b'{"value":"off-origin"}',
            ),
            24,
        ),
        (
            _Response(
                url="https://example.com/api/text",
                body=b'{"value":"wrong mime"}',
                content_type="text/plain",
            ),
            27,
        ),
        (
            _Response(
                url="https://example.com/api/large",
                body=b'{"value":"large"}',
            ),
            capture.limits.max_response_bytes + 1,
        ),
    )

    for response, body_size in responses_and_sizes:
        capture_finished_request(
            cast(Request, _Request(response, body_size)),
            capture=capture,
            authorize_url=_authorize_example_origin,
            sink=states.append,
        )

    assert states == []
    assert all(not response.body_called for response, _ in responses_and_sizes)


def test_browser_finished_request_without_size_metadata_fails_closed() -> None:
    response = _Response(
        url="https://example.com/api/state",
        body=b'{"value":"must-not-materialize"}',
    )
    capture = StructuredStateCapture(StructuredStateCaptureLimits())
    states = []

    capture_finished_request(
        cast(Request, _BrokenRequest(response, 0)),
        capture=capture,
        authorize_url=_authorize_example_origin,
        sink=states.append,
    )

    assert not response.body_called
    assert states == []


def test_browser_fixed_script_extractor_only_promotes_reviewed_sanitized_state() -> None:
    capture = StructuredStateCapture(StructuredStateCaptureLimits())
    page = _Page(
        {
            "__INITIAL_STATE__": json.dumps(
                {
                    "company": "Example",
                    "password": "drop-me",
                }
            ),
            "unreviewed": json.dumps({"should": "not-be-seen"}),
        }
    )

    captured = capture_reviewed_script_state(cast(Page, page), capture)

    assert len(page.expressions) == 1
    assert page.arguments == [capture.script_extractor_arguments()]
    assert len(captured) == 1
    assert captured[0].kind is PublicStructuredStateKind.SCRIPT_STATE
    assert captured[0].source_locator == "window.__INITIAL_STATE__"
    assert json.loads(captured[0].payload_json) == {"company": "Example"}


def _record_authorized(url: str, authorized: list[str]) -> str:
    authorized.append(url)
    return url


def _authorize_example_origin(url: str) -> str:
    if not url.startswith("https://example.com/"):
        raise RuntimeError("off-origin")
    return url


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
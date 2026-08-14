from __future__ import annotations

import json
from typing import cast

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, Request, Response

from cip.adapters.sources.public_web.browser_structured_state import (
    capture_finished_request,
    capture_reviewed_script_state,
    install_network_state_capture,
)
from cip.adapters.sources.public_web.structured_state_capture import (
    CapturedStructuredState,
    StructuredStateCapture,
    StructuredStateCaptureLimits,
)
from cip.modules.public_footprint.domain import PublicStructuredStateKind


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


class _ExplodingBodyResponse(_Response):
    def body(self) -> bytes:
        self.body_called = True
        raise ValueError("body unavailable")


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


class _NoResponseRequest(_Request):
    def response(self) -> None:
        return None


class _BrokenRequest(_Request):
    def sizes(self) -> dict[str, int]:
        return {}


class _ErrorRequest(_Request):
    def response(self) -> Response:
        raise PlaywrightError("response lookup failed")


class _Page:
    def __init__(self, raw: object) -> None:
        self.raw = raw
        self.expressions: list[str] = []
        self.arguments: list[object] = []

    def evaluate(self, expression: str, argument: object = None) -> object:
        self.expressions.append(expression)
        self.arguments.append(argument)
        return self.raw


class _ErrorPage(_Page):
    def evaluate(self, expression: str, argument: object = None) -> object:
        del expression, argument
        raise PlaywrightError("script extraction failed")


class _NoEvaluatePage:
    evaluate = None


class _ListenerPage:
    def __init__(self) -> None:
        self.event: str | None = None
        self.callback: object | None = None

    def on(self, event: str, callback: object) -> None:
        self.event = event
        self.callback = callback


class _NoListenerPage:
    on = None


def test_browser_captures_authorized_finished_same_origin_json_and_sanitizes() -> None:
    capture = StructuredStateCapture(StructuredStateCaptureLimits())
    states: list[CapturedStructuredState] = []
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


def test_browser_installs_finished_request_listener_and_listener_captures() -> None:
    capture = StructuredStateCapture(StructuredStateCaptureLimits())
    states: list[CapturedStructuredState] = []
    page = _ListenerPage()
    response = _Response(
        url="https://example.com/api/state",
        body=b'{"provider":"listener"}',
    )

    install_network_state_capture(
        cast(Page, page),
        capture=capture,
        authorize_url=_authorize_example_origin,
        sink=states.append,
    )

    assert page.event == "requestfinished"
    assert callable(page.callback)
    page.callback(cast(Request, _Request(response, len(response.body_bytes))))
    assert len(states) == 1


def test_browser_listener_and_script_capture_fail_closed_when_api_missing() -> None:
    capture = StructuredStateCapture(StructuredStateCaptureLimits())
    states: list[CapturedStructuredState] = []

    install_network_state_capture(
        cast(Page, _NoListenerPage()),
        capture=capture,
        authorize_url=_authorize_example_origin,
        sink=states.append,
    )

    assert states == []
    assert capture_reviewed_script_state(cast(Page, _NoEvaluatePage()), capture) == ()


def test_browser_finished_request_without_response_or_with_playwright_error_fails_closed() -> None:
    response = _Response(
        url="https://example.com/api/state",
        body=b'{"value":"unused"}',
    )
    capture = StructuredStateCapture(StructuredStateCaptureLimits())
    states: list[CapturedStructuredState] = []

    for request in (
        _NoResponseRequest(response, 0),
        _ErrorRequest(response, 0),
    ):
        capture_finished_request(
            cast(Request, request),
            capture=capture,
            authorize_url=_authorize_example_origin,
            sink=states.append,
        )

    assert states == []
    assert not response.body_called


def test_browser_does_not_read_off_origin_non_json_status_or_oversized_body() -> None:
    capture = StructuredStateCapture(StructuredStateCaptureLimits())
    states: list[CapturedStructuredState] = []
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
                url="https://example.com/api/error",
                body=b'{"value":"wrong status"}',
                status=503,
            ),
            28,
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


def test_browser_content_length_gate_is_fail_closed_before_body_materialization() -> None:
    capture = StructuredStateCapture(StructuredStateCaptureLimits())
    states: list[CapturedStructuredState] = []
    response = _Response(
        url="https://example.com/api/large-header",
        body=b'{"value":"small-real-body"}',
        content_length=str(capture.limits.max_response_bytes + 1),
    )

    capture_finished_request(
        cast(Request, _Request(response, len(response.body_bytes))),
        capture=capture,
        authorize_url=_authorize_example_origin,
        sink=states.append,
    )

    assert states == []
    assert not response.body_called


def test_browser_invalid_or_negative_content_length_uses_measured_body_size() -> None:
    for raw_length in ("invalid", "-1"):
        capture = StructuredStateCapture(StructuredStateCaptureLimits())
        states: list[CapturedStructuredState] = []
        response = _Response(
            url="https://example.com/api/state",
            body=b'{"value":"measured"}',
            content_length=raw_length,
        )

        capture_finished_request(
            cast(Request, _Request(response, len(response.body_bytes))),
            capture=capture,
            authorize_url=_authorize_example_origin,
            sink=states.append,
        )

        assert response.body_called
        assert len(states) == 1


def test_browser_finished_request_without_size_metadata_fails_closed() -> None:
    response = _Response(
        url="https://example.com/api/state",
        body=b'{"value":"must-not-materialize"}',
    )
    capture = StructuredStateCapture(StructuredStateCaptureLimits())
    states: list[CapturedStructuredState] = []

    capture_finished_request(
        cast(Request, _BrokenRequest(response, 0)),
        capture=capture,
        authorize_url=_authorize_example_origin,
        sink=states.append,
    )

    assert not response.body_called
    assert states == []


def test_browser_body_read_error_does_not_promote_partial_state() -> None:
    response = _ExplodingBodyResponse(
        url="https://example.com/api/state",
        body=b'{"value":"unavailable"}',
    )
    capture = StructuredStateCapture(StructuredStateCaptureLimits())
    states: list[CapturedStructuredState] = []

    capture_finished_request(
        cast(Request, _Request(response, len(response.body_bytes))),
        capture=capture,
        authorize_url=_authorize_example_origin,
        sink=states.append,
    )

    assert response.body_called
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


def test_browser_script_extractor_playwright_error_fails_closed() -> None:
    capture = StructuredStateCapture(StructuredStateCaptureLimits())

    assert capture_reviewed_script_state(cast(Page, _ErrorPage({})), capture) == ()


def _record_authorized(url: str, authorized: list[str]) -> str:
    authorized.append(url)
    return url


def _authorize_example_origin(url: str) -> str:
    if not url.startswith("https://example.com/"):
        raise RuntimeError("off-origin")
    return url
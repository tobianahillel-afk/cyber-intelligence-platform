from __future__ import annotations

from collections.abc import Callable

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, Request, Response

from cip.adapters.sources.public_web.structured_state_capture import (
    PUBLIC_SCRIPT_STATE_JS,
    CapturedStructuredState,
    StructuredStateCapture,
)

AuthorizeResponseUrl = Callable[[str], str]
CapturedStateSink = Callable[[CapturedStructuredState], None]


def install_network_state_capture(
    page: Page,
    *,
    capture: StructuredStateCapture,
    authorize_url: AuthorizeResponseUrl,
    sink: CapturedStateSink,
) -> None:
    listener = getattr(page, "on", None)
    if not callable(listener):
        return
    listener(
        "requestfinished",
        lambda request: capture_finished_request(
            request,
            capture=capture,
            authorize_url=authorize_url,
            sink=sink,
        ),
    )


def capture_finished_request(
    request: Request,
    *,
    capture: StructuredStateCapture,
    authorize_url: AuthorizeResponseUrl,
    sink: CapturedStateSink,
) -> None:
    try:
        response = request.response()
        if response is None:
            return
        sizes = request.sizes()
        body_size = int(sizes["responseBodySize"])
    except (PlaywrightError, KeyError, TypeError, ValueError):
        return
    captured = capture_response(
        response,
        body_size=body_size,
        capture=capture,
        authorize_url=authorize_url,
    )
    if captured is not None:
        sink(captured)


def capture_response(
    response: Response,
    *,
    body_size: int,
    capture: StructuredStateCapture,
    authorize_url: AuthorizeResponseUrl,
) -> CapturedStructuredState | None:
    try:
        content_type = response.header_value("content-type") or ""
        mime_type = content_type.split(";", 1)[0].strip().casefold()
        if not _json_response_candidate(response.status, mime_type):
            return None
        source_url = authorize_url(response.url)
        if not capture.admits_network_body(body_size):
            return None
        content_length = _content_length(response)
        if content_length is not None and content_length > capture.limits.max_response_bytes:
            return None
        return capture.capture_network_json(
            source_url=source_url,
            status=response.status,
            media_type=mime_type,
            body=response.body(),
        )
    except (PlaywrightError, RuntimeError, ValueError):
        return None


def capture_reviewed_script_state(
    page: Page,
    capture: StructuredStateCapture,
) -> tuple[CapturedStructuredState, ...]:
    evaluator = getattr(page, "evaluate", None)
    if not callable(evaluator):
        return ()
    try:
        raw = evaluator(
            PUBLIC_SCRIPT_STATE_JS,
            capture.script_extractor_arguments(),
        )
    except PlaywrightError:
        return ()
    return capture.capture_script_states(raw)


def _json_response_candidate(status: int, mime_type: str) -> bool:
    return 200 <= status <= 299 and (
        mime_type in {"application/json", "text/json"} or mime_type.endswith("+json")
    )


def _content_length(response: Response) -> int | None:
    raw = response.header_value("content-length")
    if raw is None:
        return None
    try:
        parsed = int(raw)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None
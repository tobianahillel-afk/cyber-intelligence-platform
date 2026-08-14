from __future__ import annotations

import json

import pytest

from cip.adapters.sources.public_web.structured_state_capture import (
    PUBLIC_SCRIPT_STATE_EXTRACTOR_ID,
    StructuredStateCapture,
    StructuredStateCaptureLimits,
)
from cip.modules.public_footprint.domain import PublicStructuredStateKind


def test_network_json_is_canonical_and_sensitive_keys_are_removed() -> None:
    capture = StructuredStateCapture(StructuredStateCaptureLimits(max_string_chars=8))

    record = capture.capture_network_json(
        source_url="https://example.com/api/state",
        status=200,
        media_type="application/json; charset=utf-8",
        body=json.dumps(
            {
                "name": "public-value",
                "accessToken": "never-store",
                "nested": {"cookie": "no", "vendor": "Splunk"},
            }
        ).encode(),
    )

    assert record is not None
    assert record.kind is PublicStructuredStateKind.NETWORK_JSON
    assert record.media_type == "application/json"
    assert json.loads(record.payload_json) == {
        "name": "public-v",
        "nested": {"vendor": "Splunk"},
    }
    assert capture.json_responses == 1
    assert capture.json_bytes > 0


@pytest.mark.parametrize("media_type", ["text/json", "application/problem+json"])
def test_network_json_accepts_reviewed_json_mime_families(media_type: str) -> None:
    capture = StructuredStateCapture(StructuredStateCaptureLimits())

    record = capture.capture_network_json(
        source_url="https://example.com/api/state",
        status=204,
        media_type=media_type,
        body=b'{"ok":true}',
    )

    assert record is not None
    assert record.media_type == media_type


@pytest.mark.parametrize(
    ("status", "media_type"),
    [(199, "application/json"), (300, "application/json"), (200, "text/html")],
)
def test_network_json_rejects_status_or_mime(status: int, media_type: str) -> None:
    capture = StructuredStateCapture(StructuredStateCaptureLimits())

    assert (
        capture.capture_network_json(
            source_url="https://example.com/api/state",
            status=status,
            media_type=media_type,
            body=b'{"ok":true}',
        )
        is None
    )


def test_network_json_rejects_malformed_oversized_and_aggregate_overflow() -> None:
    limits = StructuredStateCaptureLimits(
        max_json_responses=3,
        max_response_bytes=256,
        max_total_json_bytes=300,
    )
    capture = StructuredStateCapture(limits)

    assert (
        capture.capture_network_json(
            source_url="https://example.com/api/bad",
            status=200,
            media_type="application/json",
            body=b"{bad",
        )
        is None
    )
    assert (
        capture.capture_network_json(
            source_url="https://example.com/api/large",
            status=200,
            media_type="application/json",
            body=b"{" + (b'"a":' + b'"x"' * 100) + b"}",
        )
        is None
    )
    first = b'{"value":"' + (b"a" * 130) + b'"}'
    second = b'{"value":"' + (b"b" * 130) + b'"}'
    assert capture.capture_network_json(
        source_url="https://example.com/api/one",
        status=200,
        media_type="application/json",
        body=first,
    )
    assert (
        capture.capture_network_json(
            source_url="https://example.com/api/two",
            status=200,
            media_type="application/json",
            body=second,
        )
        is None
    )


def test_network_json_count_depth_scalar_and_key_bounds_are_deterministic() -> None:
    limits = StructuredStateCaptureLimits(
        max_json_responses=1,
        max_depth=2,
        max_scalars=2,
        max_key_chars=16,
    )
    capture = StructuredStateCapture(limits)
    body = json.dumps(
        {
            "first": 1,
            "second": 2,
            "third": 3,
            "this-key-is-far-too-long": "drop",
            "deep": {"nested": {"tooDeep": "drop"}},
        }
    ).encode()

    record = capture.capture_network_json(
        source_url="https://example.com/api/state",
        status=200,
        media_type="application/json",
        body=body,
    )

    assert record is not None
    assert json.loads(record.payload_json) == {"first": 1, "second": 2}
    assert (
        capture.capture_network_json(
            source_url="https://example.com/api/second",
            status=200,
            media_type="application/json",
            body=b'{"ok":true}',
        )
        is None
    )


def test_script_state_uses_only_fixed_public_globals_and_sanitizes() -> None:
    capture = StructuredStateCapture(StructuredStateCaptureLimits())

    records = capture.capture_script_states(
        {
            "__INITIAL_STATE__": {
                "company": "Example",
                "sessionId": "never-store",
            },
            "unsupportedGlobal": {"value": "ignored"},
        }
    )

    assert len(records) == 1
    record = records[0]
    assert record.kind is PublicStructuredStateKind.SCRIPT_STATE
    assert record.source_locator == "window.__INITIAL_STATE__"
    assert record.extractor_id == PUBLIC_SCRIPT_STATE_EXTRACTOR_ID
    assert json.loads(record.payload_json) == {"company": "Example"}


def test_script_state_count_and_total_byte_budgets_are_enforced() -> None:
    capture = StructuredStateCapture(
        StructuredStateCaptureLimits(
            max_script_states=1,
            max_total_script_bytes=256,
        )
    )

    records = capture.capture_script_states(
        {
            "__NEXT_DATA__": {"name": "first"},
            "__NUXT__": {"name": "second"},
        }
    )

    assert len(records) == 1
    assert records[0].source_locator == "window.__NEXT_DATA__"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_json_responses", 0),
        ("max_response_bytes", 255),
        ("max_total_json_bytes", 255),
        ("max_depth", 0),
        ("max_scalars", 0),
        ("max_key_chars", 15),
        ("max_string_chars", 15),
        ("max_script_states", 0),
        ("max_total_script_bytes", 255),
    ],
)
def test_structured_state_limits_fail_closed(field: str, value: int) -> None:
    kwargs = {field: value}
    with pytest.raises(ValueError, match=field):
        StructuredStateCaptureLimits(**kwargs)

from __future__ import annotations

import httpx
import pytest

from cip.modules.collection_orchestration.application.intelligence_adapter_support import (
    get_json,
)
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError

TARGET_URL = "https://provider.example.test/data"


def test_get_json_marks_rate_limit_as_retryable() -> None:
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda _request: httpx.Response(429))
        ) as client,
        pytest.raises(AdapterExecutionError) as error,
    ):
        get_json(client, TARGET_URL, headers={})

    assert error.value.error_code == "http_429"
    assert error.value.retryable is True
    assert str(error.value) == "intelligence provider returned HTTP 429"


def test_get_json_rejects_non_json_response() -> None:
    with (
        httpx.Client(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(
                    200,
                    headers={"content-type": "text/html"},
                    content=b"<html></html>",
                )
            )
        ) as client,
        pytest.raises(AdapterExecutionError) as error,
    ):
        get_json(client, TARGET_URL, headers={})

    assert error.value.error_code == "unsafe_source_response"
    assert error.value.retryable is False
    assert str(error.value) == "intelligence provider response is not JSON"


def test_get_json_rejects_response_over_explicit_bound() -> None:
    with (
        httpx.Client(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(
                    200,
                    headers={"content-type": "application/json"},
                    content=b"12345",
                )
            )
        ) as client,
        pytest.raises(AdapterExecutionError) as error,
    ):
        get_json(client, TARGET_URL, headers={}, max_bytes=4)

    assert error.value.error_code == "unsafe_source_response"
    assert str(error.value) == "intelligence provider response exceeds size limit"


@pytest.mark.parametrize("max_bytes", [0, -1, 64 * 1024 * 1024 + 1])
def test_get_json_rejects_invalid_response_bound(max_bytes: int) -> None:
    with (
        httpx.Client(transport=httpx.MockTransport(_fail_network)) as client,
        pytest.raises(ValueError, match="outside the intelligence response bound"),
    ):
        get_json(client, TARGET_URL, headers={}, max_bytes=max_bytes)


def _fail_network(_request: httpx.Request) -> httpx.Response:
    raise AssertionError("invalid bounds must fail before network")

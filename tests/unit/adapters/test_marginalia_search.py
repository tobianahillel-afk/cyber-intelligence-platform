from __future__ import annotations

import json

import httpx
import pytest

from cip.adapters.sources.marginalia_search.client import (
    MarginaliaSearchClient,
    MarginaliaSearchClientError,
)
from cip.adapters.sources.marginalia_search.registry import (
    MARGINALIA_API_HOST,
    MarginaliaSearchEntitlement,
)


def test_marginalia_entitlement_fails_closed_without_commercial_rights() -> None:
    entitlement = MarginaliaSearchEntitlement(api_key_secret_ref="secret://marginalia")

    with pytest.raises(PermissionError, match="commercial-use rights"):
        entitlement.assert_live_collection_ready()


def test_marginalia_entitlement_requires_secret_ref() -> None:
    entitlement = MarginaliaSearchEntitlement(commercial_use_rights=True)

    with pytest.raises(PermissionError, match="API-key secret ref"):
        entitlement.assert_live_collection_ready()


def test_marginalia_entitlement_accepts_only_current_api_host() -> None:
    with pytest.raises(ValueError, match="not approved"):
        MarginaliaSearchEntitlement(api_host="api.marginalia.nu")

    entitlement = _ready_entitlement()
    entitlement.assert_live_collection_ready()


def test_marginalia_client_checks_entitlement_before_network() -> None:
    network_called = False

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal network_called
        network_called = True
        raise AssertionError("network must not be reached without commercial entitlement")

    client = MarginaliaSearchClient(
        MarginaliaSearchEntitlement(api_key_secret_ref="secret://marginalia"),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(PermissionError, match="commercial-use rights"):
        client.search(query="example", api_key="commercial-test-key")
    assert network_called is False


def test_marginalia_client_rejects_shared_public_development_key() -> None:
    client = MarginaliaSearchClient(_ready_entitlement())

    with pytest.raises(PermissionError, match="public development key"):
        client.search(query="cyber security", api_key="public")


def test_marginalia_client_uses_current_api2_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == MARGINALIA_API_HOST
        assert request.url.path == "/search"
        assert request.headers["API-Key"] == "commercial-test-key"
        assert request.url.params["query"] == "example cybersecurity"
        assert request.url.params["count"] == "20"
        assert request.url.params["dc"] == "3"
        assert request.url.params["nsfw"] == "1"
        body = {
            "query": "example cybersecurity",
            "license": "commercial",
            "results": [
                {
                    "url": "https://example.com/security",
                    "title": "Security",
                    "description": "Public result metadata",
                }
            ],
        }
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=json.dumps(body).encode(),
        )

    client = MarginaliaSearchClient(
        _ready_entitlement(),
        transport=httpx.MockTransport(handler),
    )
    result = client.search(
        query="example cybersecurity",
        api_key="commercial-test-key",
    )

    assert result.response.query == "example cybersecurity"
    assert result.response.results[0].url == "https://example.com/security"
    assert result.request_url.startswith("https://api2.marginalia-search.com/search?")


def test_marginalia_client_rejects_oversized_response_while_streaming() -> None:
    oversized = b"x" * (2 * 1024 * 1024 + 1)
    client = MarginaliaSearchClient(
        _ready_entitlement(),
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                headers={"content-type": "application/json"},
                content=oversized,
            )
        ),
    )

    with pytest.raises(MarginaliaSearchClientError) as error:
        client.search(query="example", api_key="commercial-test-key")
    assert error.value.code == "unsafe_source_response"
    assert error.value.retryable is False


def test_marginalia_client_classifies_http_and_schema_failures() -> None:
    throttled = MarginaliaSearchClient(
        _ready_entitlement(),
        transport=httpx.MockTransport(lambda _: httpx.Response(429)),
    )
    with pytest.raises(MarginaliaSearchClientError) as http_error:
        throttled.search(query="example", api_key="commercial-test-key")
    assert http_error.value.code == "http_429"
    assert http_error.value.retryable is True

    drifted = MarginaliaSearchClient(
        _ready_entitlement(),
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                headers={"content-type": "application/json"},
                content=b'{"unexpected": true}',
            )
        ),
    )
    with pytest.raises(MarginaliaSearchClientError) as schema_error:
        drifted.search(query="example", api_key="commercial-test-key")
    assert schema_error.value.code == "source_schema_drift"
    assert schema_error.value.retryable is False


def _ready_entitlement() -> MarginaliaSearchEntitlement:
    return MarginaliaSearchEntitlement(
        api_host=MARGINALIA_API_HOST,
        commercial_use_rights=True,
        api_key_secret_ref="secret://marginalia/commercial",
    )

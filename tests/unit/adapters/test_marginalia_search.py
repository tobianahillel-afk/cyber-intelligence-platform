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

    entitlement = MarginaliaSearchEntitlement(
        api_host=MARGINALIA_API_HOST,
        commercial_use_rights=True,
        api_key_secret_ref="secret://marginalia/commercial",
    )
    entitlement.assert_live_collection_ready()


def test_marginalia_client_rejects_shared_public_development_key() -> None:
    client = MarginaliaSearchClient()

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

    client = MarginaliaSearchClient(transport=httpx.MockTransport(handler))
    result = client.search(
        query="example cybersecurity",
        api_key="commercial-test-key",
    )

    assert result.response.query == "example cybersecurity"
    assert result.response.results[0].url == "https://example.com/security"
    assert result.request_url.startswith("https://api2.marginalia-search.com/search?")


def test_marginalia_client_classifies_http_and_schema_failures() -> None:
    throttled = MarginaliaSearchClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(429))
    )
    with pytest.raises(MarginaliaSearchClientError) as http_error:
        throttled.search(query="example", api_key="commercial-test-key")
    assert http_error.value.code == "http_429"
    assert http_error.value.retryable is True

    drifted = MarginaliaSearchClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                headers={"content-type": "application/json"},
                content=b'{"unexpected": true}',
            )
        )
    )
    with pytest.raises(MarginaliaSearchClientError) as schema_error:
        drifted.search(query="example", api_key="commercial-test-key")
    assert schema_error.value.code == "source_schema_drift"
    assert schema_error.value.retryable is False

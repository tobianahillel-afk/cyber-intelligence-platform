from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest

from cip.adapters.sources.mojeek_search.registry import (
    MojeekSearchEntitlement,
    load_mojeek_search_entitlement,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.mojeek_search_adapter import (
    MojeekSearchAdapter,
)
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.public_footprint.domain.search import SearchQueryTemplate
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 11, 15, 25, tzinfo=UTC)
RETENTION = NOW + timedelta(days=90)
ORG_ID = UUID("74b2a087-10ce-5d99-a90c-5aa1c0fabf6f")
POLICY_PATH = Path("policies/sources.search_archives.yml")
ENTITLEMENT_PATH = Path("policies/mojeek_search_entitlement.yml")


def test_checked_in_mojeek_entitlement_is_fail_closed() -> None:
    entitlement = load_mojeek_search_entitlement(ENTITLEMENT_PATH)
    assert entitlement.durable_storage_authorized is False
    assert entitlement.plan == "unprovisioned"
    assert entitlement.evidence_reference is None


def test_mojeek_empty_target_uses_no_entitlement_secret_or_network() -> None:
    token_calls = 0

    def token_provider() -> str:
        nonlocal token_calls
        token_calls += 1
        return "secret"

    def fail_network(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be used without enabled target")

    batch = _collect(
        MojeekSearchAdapter(
            _entry(),
            (_target(enabled=False),),
            (_template(),),
            _entitlement(authorized=False),
            token_provider=token_provider,
            transport=httpx.MockTransport(fail_network),
        )
    )
    assert batch.not_modified is True
    assert batch.observations == ()
    assert token_calls == 0


def test_mojeek_missing_storage_entitlement_stops_before_secret_and_network() -> None:
    token_calls = 0

    def token_provider() -> str:
        nonlocal token_calls
        token_calls += 1
        return "secret"

    def fail_network(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be used without storage entitlement")

    adapter = MojeekSearchAdapter(
        _entry(),
        (_target(),),
        (_template(),),
        _entitlement(authorized=False),
        token_provider=token_provider,
        transport=httpx.MockTransport(fail_network),
    )
    with pytest.raises(AdapterExecutionError) as exc_info:
        _collect(adapter)
    assert exc_info.value.error_code == "provider_storage_entitlement_missing"
    assert exc_info.value.retryable is False
    assert token_calls == 0


def test_mojeek_missing_secret_stops_before_network() -> None:
    adapter = MojeekSearchAdapter(
        _entry(),
        (_target(),),
        (_template(),),
        _entitlement(),
        token_provider=lambda: None,
        transport=httpx.MockTransport(
            lambda _request: (_ for _ in ()).throw(
                AssertionError("network must not be used without provider secret")
            )
        ),
    )
    with pytest.raises(AdapterExecutionError) as exc_info:
        _collect(adapter)
    assert exc_info.value.error_code == "provider_not_connected"
    assert exc_info.value.retryable is False


def test_mojeek_maps_bounded_safe_result_metadata_only() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={
                "response": {
                    "status": "OK",
                    "head": {"ignored": True},
                    "results": [
                        {
                            "url": "https://example.com/security",
                            "title": "Example security",
                            "desc": "Public search snippet",
                            "score": 999,
                            "image": {"url": "https://images.example/image.jpg"},
                        },
                        {
                            "url": "javascript:alert(1)",
                            "title": "Unsafe",
                            "desc": "discard me",
                        },
                    ],
                }
            },
            request=request,
        )

    batch = _collect(
        MojeekSearchAdapter(
            _entry(),
            (_target(),),
            (_template(),),
            _entitlement(),
            token_provider=lambda: "provider-key",
            transport=httpx.MockTransport(handler),
        )
    )
    assert len(requests) == 1
    request = requests[0]
    assert request.url.path == "/search"
    assert request.url.params["api_key"] == "provider-key"
    assert request.url.params["q"] == '"Example Corp" security'
    assert request.url.params["t"] == "20"
    assert request.url.params["fmt"] == "json"
    assert len(batch.observations) == 1
    assert len(batch.public_footprint_projections) == 1
    projection = batch.public_footprint_projections[0]
    assert projection.claims == ()
    assert projection.resource.canonical_url == "https://example.com/security"
    assert projection.resource.retrieval_state.value == "quarantined"
    assert projection.version.excerpt == "Public search snippet"
    assert "provider-key" not in batch.observations[0].source_url


def test_mojeek_checkpoint_schema_drift_provider_status_and_429_fail_closed() -> None:
    adapter = MojeekSearchAdapter(
        _entry(),
        (_target(),),
        (_template(),),
        _entitlement(),
        token_provider=lambda: "key",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, request=request)),
    )
    with pytest.raises(AdapterExecutionError) as checkpoint_info:
        _collect(adapter, checkpoint_payload={"pair_index": True})
    assert checkpoint_info.value.error_code == "invalid_checkpoint"

    def malformed(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b"not-json",
            request=request,
        )

    with pytest.raises(AdapterExecutionError) as schema_info:
        _collect(
            MojeekSearchAdapter(
                _entry(),
                (_target(),),
                (_template(),),
                _entitlement(),
                token_provider=lambda: "key",
                transport=httpx.MockTransport(malformed),
            )
        )
    assert schema_info.value.error_code == "source_schema_drift"

    def provider_error(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"response": {"status": "ERROR: Daily Limit Reached", "results": []}},
            request=request,
        )

    with pytest.raises(AdapterExecutionError) as provider_info:
        _collect(
            MojeekSearchAdapter(
                _entry(),
                (_target(),),
                (_template(),),
                _entitlement(),
                token_provider=lambda: "key",
                transport=httpx.MockTransport(provider_error),
            )
        )
    assert provider_info.value.error_code == "provider_response_error"

    def rate_limited(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, request=request)

    with pytest.raises(AdapterExecutionError) as rate_info:
        _collect(
            MojeekSearchAdapter(
                _entry(),
                (_target(),),
                (_template(),),
                _entitlement(),
                token_provider=lambda: "key",
                transport=httpx.MockTransport(rate_limited),
            )
        )
    assert rate_info.value.error_code == "http_429"
    assert rate_info.value.retryable is True


def test_mojeek_authorized_entitlement_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence reference"):
        MojeekSearchEntitlement(
            durable_storage_authorized=True,
            plan="business",
            evidence_reference=None,
        )


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(POLICY_PATH)
        if entry.policy.id == "mojeek-web-search-metadata"
    )


def _target(*, enabled: bool = True) -> PublicWebTarget:
    return PublicWebTarget(
        id="example-corp",
        organization_id=ORG_ID,
        canonical_name="Example Corp",
        base_url="https://example.com/",
        sitemap_urls=("https://example.com/sitemap.xml",),
        allowed_path_prefixes=("/",),
        enabled=enabled,
        authorization_reference="controlled-test-target",
        authorization_reviewed_at=NOW,
    )


def _template() -> SearchQueryTemplate:
    return SearchQueryTemplate(
        id="security-context",
        version=1,
        query_pattern='"{organization}" security',
        purpose="corporate-public-footprint",
        enabled=True,
    )


def _entitlement(*, authorized: bool = True) -> MojeekSearchEntitlement:
    return MojeekSearchEntitlement(
        durable_storage_authorized=authorized,
        plan="business" if authorized else "unprovisioned",
        evidence_reference="controlled-test-entitlement" if authorized else None,
    )


def _collect(
    adapter: MojeekSearchAdapter,
    *,
    checkpoint_payload: dict[str, object] | None = None,
):
    return adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=checkpoint_payload,
        collected_at=NOW,
        retention_until=RETENTION,
    )

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest

from cip.adapters.sources.marginalia_search.registry import MarginaliaSearchEntitlement
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.marginalia_search_adapter import (
    MarginaliaSearchAdapter,
)
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.public_footprint.domain.search import SearchQueryTemplate
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 12, 17, 50, tzinfo=UTC)
RETENTION = NOW + timedelta(days=90)
ORG_ID = UUID("b05a6206-c42d-55b7-bcb9-727b0203bc50")
POLICY_PATH = Path("policies/sources.search_providers_sa15.yml")


def test_checked_in_marginalia_policy_denies_before_secret_and_network() -> None:
    token_calls = 0

    def token_provider() -> str:
        nonlocal token_calls
        token_calls += 1
        return "commercial-test-key"

    adapter = MarginaliaSearchAdapter(
        _checked_in_entry(),
        (_target(),),
        (_template(),),
        _ready_entitlement(),
        token_provider=token_provider,
        transport=httpx.MockTransport(
            lambda _: (_ for _ in ()).throw(
                AssertionError("network must not run while source governance is missing")
            )
        ),
    )

    with pytest.raises(AdapterExecutionError) as exc_info:
        _collect(adapter)
    assert exc_info.value.error_code == "source_policy_denied"
    assert exc_info.value.retryable is False
    assert token_calls == 0


def test_marginalia_disabled_target_uses_no_entitlement_secret_or_network() -> None:
    token_calls = 0

    def token_provider() -> str:
        nonlocal token_calls
        token_calls += 1
        return "commercial-test-key"

    batch = _collect(
        MarginaliaSearchAdapter(
            _authorized_entry(),
            (_target(enabled=False),),
            (_template(),),
            MarginaliaSearchEntitlement(),
            token_provider=token_provider,
            transport=httpx.MockTransport(
                lambda _: (_ for _ in ()).throw(
                    AssertionError("network must not run without enabled target")
                )
            ),
        )
    )
    assert batch.not_modified is True
    assert batch.observations == ()
    assert token_calls == 0


def test_marginalia_missing_entitlement_stops_before_secret_and_network() -> None:
    token_calls = 0

    def token_provider() -> str:
        nonlocal token_calls
        token_calls += 1
        return "commercial-test-key"

    adapter = MarginaliaSearchAdapter(
        _authorized_entry(),
        (_target(),),
        (_template(),),
        MarginaliaSearchEntitlement(api_key_secret_ref="secret://marginalia"),
        token_provider=token_provider,
        transport=httpx.MockTransport(
            lambda _: (_ for _ in ()).throw(
                AssertionError("network must not run without commercial entitlement")
            )
        ),
    )

    with pytest.raises(AdapterExecutionError) as exc_info:
        _collect(adapter)
    assert exc_info.value.error_code == "provider_commercial_entitlement_missing"
    assert exc_info.value.retryable is False
    assert token_calls == 0


def test_marginalia_missing_runtime_secret_stops_before_network() -> None:
    adapter = MarginaliaSearchAdapter(
        _authorized_entry(),
        (_target(),),
        (_template(),),
        _ready_entitlement(),
        token_provider=lambda: None,
        transport=httpx.MockTransport(
            lambda _: (_ for _ in ()).throw(
                AssertionError("network must not run without runtime provider secret")
            )
        ),
    )

    with pytest.raises(AdapterExecutionError) as exc_info:
        _collect(adapter)
    assert exc_info.value.error_code == "provider_not_connected"
    assert exc_info.value.retryable is False


def test_marginalia_maps_bounded_safe_result_metadata_only() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={
                "query": "Example Corp cybersecurity",
                "license": "commercial",
                "results": [
                    {
                        "url": "https://example.com/security",
                        "title": "Example security",
                        "description": "Public search snippet",
                    },
                    {
                        "url": "javascript:alert(1)",
                        "title": "Unsafe",
                        "description": "discard me",
                    },
                ],
            },
            request=request,
        )

    batch = _collect(
        MarginaliaSearchAdapter(
            _authorized_entry(),
            (_target(),),
            (_template(),),
            _ready_entitlement(),
            token_provider=lambda: "commercial-test-key",
            transport=httpx.MockTransport(handler),
        )
    )

    assert len(requests) == 1
    request = requests[0]
    assert request.url.host == "api2.marginalia-search.com"
    assert request.url.path == "/search"
    assert request.headers["API-Key"] == "commercial-test-key"
    assert request.url.params["query"] == "Example Corp cybersecurity"
    assert len(batch.observations) == 1
    assert len(batch.public_footprint_projections) == 1
    observation = batch.observations[0]
    projection = batch.public_footprint_projections[0]
    assert observation.source_id == "marginalia-web-search-metadata"
    assert "commercial-test-key" not in observation.source_url
    assert projection.claims == ()
    assert projection.resource.canonical_url == "https://example.com/security"
    assert projection.resource.retrieval_state.value == "quarantined"
    assert projection.version.excerpt == "Public search snippet"
    assert batch.checkpoint_payload == {"pair_index": 0}


def test_marginalia_invalid_checkpoint_and_429_fail_closed() -> None:
    adapter = MarginaliaSearchAdapter(
        _authorized_entry(),
        (_target(),),
        (_template(),),
        _ready_entitlement(),
        token_provider=lambda: "commercial-test-key",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, request=request)),
    )
    with pytest.raises(AdapterExecutionError) as checkpoint_info:
        _collect(adapter, checkpoint_payload={"pair_index": True})
    assert checkpoint_info.value.error_code == "invalid_checkpoint"

    rate_limited = MarginaliaSearchAdapter(
        _authorized_entry(),
        (_target(),),
        (_template(),),
        _ready_entitlement(),
        token_provider=lambda: "commercial-test-key",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(429, request=request)
        ),
    )
    with pytest.raises(AdapterExecutionError) as rate_info:
        _collect(rate_limited)
    assert rate_info.value.error_code == "http_429"
    assert rate_info.value.retryable is True


def _checked_in_entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(POLICY_PATH)
        if entry.policy.id == "marginalia-web-search-metadata"
    )


def _authorized_entry() -> SourceRegistryEntry:
    return SourceRegistryEntry(
        policy=SourcePolicy(
            id="marginalia-web-search-metadata",
            name="Marginalia Search API metadata",
            base_url="https://api2.marginalia-search.com/search",
            status=SourceStatus.ENABLED,
            source_type=SourceType.SEARCH_PROVIDER,
            owner="Marginalia Search",
            terms_url="https://about.marginalia-search.com/article/api/",
            licence="controlled test-only commercial authorization",
            allowed_data_categories=frozenset({DataCategory.PUBLIC_RESULT_METADATA}),
            retention_days=90,
            raw_content_storage=False,
            human_review_required=False,
        ),
        authorization=SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="controlled-test-only-authorization",
            reviewed_at=NOW,
            approved_hosts=frozenset({"api2.marginalia-search.com"}),
            approved_path_prefixes=("/search",),
            approved_purposes=frozenset({"corporate-public-footprint"}),
            automated_collection_allowed=True,
            raw_storage_allowed=False,
        ),
        economics={},
        notes="test-only authorization; not production activation truth",
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
        query_pattern="{organization} cybersecurity",
        purpose="corporate-public-footprint",
        enabled=True,
    )


def _ready_entitlement() -> MarginaliaSearchEntitlement:
    return MarginaliaSearchEntitlement(
        commercial_use_rights=True,
        api_key_secret_ref="secret://marginalia/commercial",
        plan="commercial",
        evidence_reference="controlled-test-entitlement",
    )


def _collect(
    adapter: MarginaliaSearchAdapter,
    *,
    checkpoint_payload: dict[str, object] | None = None,
):
    return adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=checkpoint_payload,
        collected_at=NOW,
        retention_until=RETENTION,
    )

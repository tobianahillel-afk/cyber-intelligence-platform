from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from cip.adapters.sources.passive_infrastructure.registry import PassiveInfrastructureTarget
from cip.modules.collection_orchestration.application.certspotter_adapter import (
    CertSpotterAdapter,
)
from cip.modules.collection_orchestration.application.cloudflare_dns_adapter import (
    CloudflareDnsAdapter,
)
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.passive_exposure.domain.models import (
    AttributionRisk,
    OrganizationLinkStatus,
    PassiveAssetKind,
    PassiveObservationKind,
    PassiveObservationState,
)
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 9, 22, 30, tzinfo=UTC)
RETENTION = NOW + timedelta(days=365)
JOB_ID = UUID("00000000-0000-0000-0000-000000000303")
ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000000304")
REGISTRY = Path("policies/sources.passive_infrastructure.yml")


def test_cloudflare_maps_only_passive_review_required_dns_observations() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        record_type = request.url.params["type"]
        data = "8.8.8.8" if record_type == "A" else "2606:4700:4700::1111"
        numeric_type = 1 if record_type == "A" else 28
        return _json_response(
            {
                "Status": 0,
                "Question": [{"name": "example.com", "type": numeric_type}],
                "Answer": [
                    {
                        "name": "example.com",
                        "type": numeric_type,
                        "TTL": 300,
                        "data": data,
                    }
                ],
            }
        )

    adapter = CloudflareDnsAdapter(
        _entry("cloudflare-doh"),
        (_target(),),
        transport=httpx.MockTransport(handler),
    )
    batch = _collect(adapter)

    assert len(requests) == 2
    assert {request.url.params["type"] for request in requests} == {"A", "AAAA"}
    assert all(request.url.host == "cloudflare-dns.com" for request in requests)
    assert all(request.headers["accept"] == "application/dns-json" for request in requests)
    assert len(batch.observations) == 2
    assert len(batch.passive_exposure_projections) == 2
    assert {
        snapshot.asset.kind for snapshot in batch.passive_exposure_projections
    } == {PassiveAssetKind.IPV4, PassiveAssetKind.IPV6}
    for snapshot in batch.passive_exposure_projections:
        assert snapshot.observation_kind is PassiveObservationKind.PASSIVE_DNS
        assert snapshot.organization_link.status is OrganizationLinkStatus.REVIEW_REQUIRED
        assert AttributionRisk.SHARED_HOSTING in snapshot.organization_link.attribution_risks
        assert snapshot.active_probe_performed is False
        assert snapshot.direct_validation_performed is False
        assert snapshot.vulnerability_applicability_assessed is False
        assert snapshot.exposure_verified is False
        assert snapshot.can_support_exposure_conclusion is False


def test_cloudflare_without_targets_performs_no_network() -> None:
    adapter = CloudflareDnsAdapter(
        _entry("cloudflare-doh"),
        (),
        transport=httpx.MockTransport(_fail_network),
    )

    batch = _collect(adapter)

    assert batch.not_modified is True
    assert batch.observations == ()
    assert batch.passive_exposure_projections == ()


def test_cloudflare_discards_non_global_dns_answers() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        record_type = request.url.params["type"]
        numeric_type = 1 if record_type == "A" else 28
        data = "192.168.1.20" if record_type == "A" else "fe80::1"
        return _json_response(
            {
                "Status": 0,
                "Answer": [
                    {
                        "name": "example.com",
                        "type": numeric_type,
                        "TTL": 60,
                        "data": data,
                    }
                ],
            }
        )

    adapter = CloudflareDnsAdapter(
        _entry("cloudflare-doh"),
        (_target(),),
        transport=httpx.MockTransport(handler),
    )

    batch = _collect(adapter)

    assert batch.not_modified is True
    assert batch.passive_exposure_projections == ()


def test_certspotter_without_targets_skips_secret_and_network() -> None:
    secret_calls = 0

    def token_provider() -> str:
        nonlocal secret_calls
        secret_calls += 1
        return "unused"

    adapter = CertSpotterAdapter(
        _entry("certspotter-ct"),
        (),
        token_provider=token_provider,
        transport=httpx.MockTransport(_fail_network),
    )

    batch = _collect(adapter)

    assert batch.not_modified is True
    assert secret_calls == 0


def test_certspotter_fails_closed_without_connected_secret() -> None:
    adapter = CertSpotterAdapter(
        _entry("certspotter-ct"),
        (_target(),),
        token_provider=lambda: None,
        transport=httpx.MockTransport(_fail_network),
    )

    with pytest.raises(AdapterExecutionError) as error:
        _collect(adapter)

    assert error.value.error_code == "provider_not_connected"
    assert error.value.retryable is False


def test_certspotter_maps_scoped_wildcard_certificate_without_exposure_claim() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _json_response(
            [
                {
                    "id": "issuance-1",
                    "tbs_sha256": "a" * 64,
                    "dns_names": ["*.example.com", "other.example.net"],
                    "not_before": "2026-08-01T00:00:00Z",
                    "not_after": "2026-10-01T00:00:00Z",
                },
                {
                    "id": "out-of-scope",
                    "tbs_sha256": "b" * 64,
                    "dns_names": ["unrelated.test.invalid"],
                    "not_before": "2026-08-01T00:00:00Z",
                    "not_after": "2026-10-01T00:00:00Z",
                },
            ]
        )

    adapter = CertSpotterAdapter(
        _entry("certspotter-ct"),
        (_target(),),
        token_provider=lambda: "test-api-token",
        transport=httpx.MockTransport(handler),
    )
    batch = _collect(adapter)

    assert len(requests) == 1
    request = requests[0]
    assert request.url.host == "api.certspotter.com"
    assert request.url.params["domain"] == "example.com"
    assert request.url.params["include_subdomains"] == "true"
    assert request.headers["Authorization"] == "Bearer test-api-token"
    assert len(batch.observations) == 1
    assert len(batch.passive_exposure_projections) == 1
    assert batch.checkpoint_payload["after_by_target"] == {
        "example-target": "out-of-scope"
    }
    raw = batch.observations[0]
    assert raw.payload_reference is None
    assert "test-api-token" not in raw.source_url
    snapshot = batch.passive_exposure_projections[0]
    assert snapshot.source_record_key == "issuance-1"
    assert snapshot.asset.kind is PassiveAssetKind.CERTIFICATE
    assert snapshot.asset.value == "a" * 64
    assert snapshot.observation_kind is PassiveObservationKind.CERTIFICATE
    assert snapshot.state is PassiveObservationState.CURRENT
    assert snapshot.organization_link.status is OrganizationLinkStatus.REVIEW_REQUIRED
    assert snapshot.exposure_verified is False
    assert snapshot.can_support_exposure_conclusion is False


def test_certspotter_reuses_provider_after_cursor_on_next_collection() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return _json_response(
                [
                    {
                        "id": "cursor-1",
                        "tbs_sha256": "d" * 64,
                        "dns_names": ["example.com"],
                        "not_before": "2026-08-01T00:00:00Z",
                        "not_after": "2026-10-01T00:00:00Z",
                    }
                ]
            )
        return _json_response([])

    adapter = CertSpotterAdapter(
        _entry("certspotter-ct"),
        (_target(),),
        token_provider=lambda: "test-api-token",
        transport=httpx.MockTransport(handler),
    )
    first = _collect(adapter)
    second = adapter.collect(
        collection_job_id=JOB_ID,
        checkpoint_payload=first.checkpoint_payload,
        collected_at=NOW + timedelta(minutes=5),
        retention_until=RETENTION,
    )

    assert "after" not in requests[0].url.params
    assert requests[1].url.params["after"] == "cursor-1"
    assert second.not_modified is True
    assert second.checkpoint_payload["after_by_target"] == {
        "example-target": "cursor-1"
    }


def test_certspotter_marks_expired_issuance_inactive() -> None:
    adapter = CertSpotterAdapter(
        _entry("certspotter-ct"),
        (_target(),),
        token_provider=lambda: "test-api-token",
        transport=httpx.MockTransport(
            lambda _request: _json_response(
                [
                    {
                        "id": "expired-1",
                        "tbs_sha256": "c" * 64,
                        "dns_names": ["example.com"],
                        "not_before": "2025-01-01T00:00:00Z",
                        "not_after": "2025-12-31T00:00:00Z",
                    }
                ]
            )
        ),
    )

    batch = _collect(adapter)
    snapshot = batch.passive_exposure_projections[0]

    assert snapshot.state is PassiveObservationState.EXPIRED
    assert snapshot.active is False
    assert snapshot.can_support_exposure_conclusion is False


def _collect(adapter: CloudflareDnsAdapter | CertSpotterAdapter):
    return adapter.collect(
        collection_job_id=JOB_ID,
        checkpoint_payload=None,
        collected_at=NOW,
        retention_until=RETENTION,
    )


def _entry(source_id: str) -> SourceRegistryEntry:
    entries = {entry.policy.id: entry for entry in load_source_registry(REGISTRY)}
    return entries[source_id]


def _target() -> PassiveInfrastructureTarget:
    return PassiveInfrastructureTarget(
        target_id="example-target",
        organization_id=ORGANIZATION_ID,
        domain="example.com",
        enabled=True,
    )


def _json_response(payload: object) -> httpx.Response:
    return httpx.Response(
        200,
        headers={"content-type": "application/json"},
        content=json.dumps(payload).encode("utf-8"),
    )


def _fail_network(_request: httpx.Request) -> httpx.Response:
    raise AssertionError("network must not run")

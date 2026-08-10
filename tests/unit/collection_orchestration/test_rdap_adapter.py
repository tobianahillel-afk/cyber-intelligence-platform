from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from cip.adapters.sources.passive_infrastructure.rdap_registry import (
    RdapTarget,
    RdapTargetKind,
)
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.collection_orchestration.application.rdap_adapter import IanaRdapAdapter
from cip.modules.passive_exposure.domain.models import (
    AttributionRisk,
    OrganizationLinkStatus,
    PassiveAssetKind,
    PassiveObservationKind,
)
from cip.modules.source_governance.infrastructure.registry import load_source_registry

NOW = datetime(2026, 8, 10, 10, 45, tzinfo=UTC)
RETENTION = NOW + timedelta(days=365)
JOB_ID = UUID("00000000-0000-0000-0000-000000000801")
ORG_ID = UUID("00000000-0000-0000-0000-000000000802")
POLICY_PATH = Path("policies/sources.passive_infrastructure.yml")


def test_empty_rdap_targets_perform_no_network() -> None:
    adapter = IanaRdapAdapter(
        _entry(),
        (),
        transport=httpx.MockTransport(_fail_network),
    )

    batch = _collect(adapter)

    assert batch.not_modified is True
    assert batch.passive_exposure_projections == ()


def test_domain_rdap_uses_iana_bootstrap_and_excludes_contact_semantics() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "data.iana.org":
            return _json(_bootstrap([["com"], ["https://rdap.registry.test/"]]))
        return _json(
            {
                "objectClassName": "domain",
                "handle": "EXAMPLE-COM",
                "ldhName": "example.com",
                "status": ["active"],
                "entities": [
                    {
                        "handle": "private-person",
                        "vcardArray": ["vcard", [["email", {}, "text", "private@example.com"]]],
                    }
                ],
            },
            content_type="application/rdap+json",
        )

    adapter = IanaRdapAdapter(
        _entry(),
        (_target(RdapTargetKind.DOMAIN, "example.com"),),
        transport=httpx.MockTransport(handler),
    )
    batch = _collect(adapter)

    assert [request.url.host for request in requests] == [
        "data.iana.org",
        "rdap.registry.test",
    ]
    assert requests[1].url.path == "/domain/example.com"
    snapshot = batch.passive_exposure_projections[0]
    assert snapshot.asset.kind is PassiveAssetKind.DOMAIN
    assert snapshot.asset.value == "example.com"
    assert snapshot.observation_kind is PassiveObservationKind.REGISTRATION
    assert snapshot.organization_link.status is OrganizationLinkStatus.REVIEW_REQUIRED
    assert snapshot.organization_link.attribution_risks == (
        AttributionRisk.ABANDONED_DOMAIN,
    )
    assert batch.observations[0].source_url == "https://rdap.registry.test/domain/example.com"


def test_ipv4_rdap_chooses_longest_prefix_bootstrap_match() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "data.iana.org":
            return _json(
                _bootstrap_services(
                    [
                        [["8.0.0.0/8"], ["https://broad.example.test/"]],
                        [["8.8.8.0/24"], ["https://specific.example.test/rdap/"]],
                    ]
                )
            )
        return _json(
            {
                "objectClassName": "ip network",
                "handle": "NET-8-8-8-0-1",
                "startAddress": "8.8.8.0",
                "endAddress": "8.8.8.255",
                "ipVersion": "v4",
            },
            content_type="application/rdap+json",
        )

    adapter = IanaRdapAdapter(
        _entry(),
        (_target(RdapTargetKind.IPV4, "8.8.8.8"),),
        transport=httpx.MockTransport(handler),
    )
    batch = _collect(adapter)

    assert requests[1].url.host == "specific.example.test"
    assert requests[1].url.path == "/rdap/ip/8.8.8.8"
    snapshot = batch.passive_exposure_projections[0]
    assert snapshot.asset.kind is PassiveAssetKind.IPV4
    assert snapshot.organization_link.attribution_risks == (
        AttributionRisk.REASSIGNED_ADDRESS,
    )


def test_asn_rdap_uses_matching_range_and_validates_response_range() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "data.iana.org":
            return _json(
                _bootstrap([["64496-64510"], ["https://rir.example.test/rdap/"]])
            )
        return _json(
            {
                "objectClassName": "autnum",
                "handle": "AS64497",
                "startAutnum": 64496,
                "endAutnum": 64510,
                "name": "EXAMPLE-NET",
            },
            content_type="application/rdap+json",
        )

    adapter = IanaRdapAdapter(
        _entry(),
        (_target(RdapTargetKind.ASN, "AS64497"),),
        transport=httpx.MockTransport(handler),
    )
    batch = _collect(adapter)

    snapshot = batch.passive_exposure_projections[0]
    assert snapshot.asset.kind is PassiveAssetKind.ASN
    assert snapshot.asset.value == "AS64497"
    assert snapshot.organization_link.attribution_risks == (AttributionRisk.RESELLER,)


def test_rdap_rejects_non_https_bootstrap_endpoint_before_second_hop() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _json(_bootstrap([["com"], ["http://unsafe.example.test/rdap/"]]))

    adapter = IanaRdapAdapter(
        _entry(),
        (_target(RdapTargetKind.DOMAIN, "example.com"),),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(AdapterExecutionError) as error:
        _collect(adapter)

    assert error.value.error_code == "rdap_bootstrap_error"
    assert len(requests) == 1


def test_rdap_rejects_response_that_does_not_cover_target() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "data.iana.org":
            return _json(_bootstrap([["com"], ["https://rdap.registry.test/"]]))
        return _json(
            {"objectClassName": "domain", "ldhName": "other.example"},
            content_type="application/rdap+json",
        )

    adapter = IanaRdapAdapter(
        _entry(),
        (_target(RdapTargetKind.DOMAIN, "example.com"),),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(AdapterExecutionError) as error:
        _collect(adapter)

    assert error.value.error_code == "source_identity_mismatch"


def _collect(adapter: IanaRdapAdapter):
    return adapter.collect(
        collection_job_id=JOB_ID,
        checkpoint_payload=None,
        collected_at=NOW,
        retention_until=RETENTION,
    )


def _entry():
    entries = load_source_registry(POLICY_PATH)
    return {entry.policy.id: entry for entry in entries}[IanaRdapAdapter.source_id]


def _target(kind: RdapTargetKind, value: str) -> RdapTarget:
    return RdapTarget(
        target_id=f"target-{kind.value}",
        organization_id=ORG_ID,
        kind=kind,
        value=value,
        enabled=True,
    )


def _bootstrap(service: list[list[str]]) -> dict[str, object]:
    return _bootstrap_services([service])


def _bootstrap_services(services: list[list[list[str]]]) -> dict[str, object]:
    return {
        "version": "1.0",
        "publication": "2026-08-10T00:00:00Z",
        "services": services,
    }


def _json(payload: object, *, content_type: str = "application/json") -> httpx.Response:
    return httpx.Response(
        200,
        headers={"content-type": content_type},
        content=json.dumps(payload).encode("utf-8"),
    )


def _fail_network(_request: httpx.Request) -> httpx.Response:
    raise AssertionError("network must not run")

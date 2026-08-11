from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest

from cip.adapters.sources.w3c_standards.registry import (
    W3cAffiliationTarget,
    load_w3c_affiliation_targets,
)
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.collection_orchestration.application.w3c_standard_adapter import W3cStandardAdapter
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 11, 14, 5, tzinfo=UTC)
RETENTION = NOW + timedelta(days=180)
ORG_ID = UUID("74b2a087-10ce-5d99-a90c-5aa1c0fabf6f")
POLICY_PATH = Path("policies/sources.search_archives.yml")
TARGET_PATH = Path("policies/w3c_affiliation_targets.yml")
AFFILIATION_NAME = "Lawrence Berkeley National Laboratory"


def test_checked_in_w3c_registry_is_empty_and_disabled_target_uses_no_network() -> None:
    assert load_w3c_affiliation_targets(TARGET_PATH) == ()

    def fail_network(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be used without enabled target")

    batch = _collect(
        W3cStandardAdapter(
            _entry(),
            (_target(enabled=False),),
            transport=httpx.MockTransport(fail_network),
        )
    )
    assert batch.not_modified is True
    assert batch.observations == ()
    assert batch.checkpoint_payload == {"target_index": 0}


def test_w3c_maps_only_safe_group_specification_metadata() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/affiliations/1015":
            payload = {"id": 1015, "name": AFFILIATION_NAME}
        elif request.url.path == "/affiliations/1015/participations":
            payload = {
                "_embedded": {
                    "participations": [
                        {
                            "_links": {
                                "group": {"href": "https://api.w3.org/groups/wg/das"},
                                "participants": {
                                    "href": "https://api.w3.org/participations/38929/participants"
                                },
                            }
                        },
                        {
                            "_links": {
                                "group": {"href": "https://evil.example/groups/wg/ignored"}
                            }
                        },
                    ]
                }
            }
        elif request.url.path == "/groups/wg/das/specifications":
            payload = {
                "_embedded": {
                    "specifications": [
                        {
                            "shortname": "dap-api-reqs",
                            "title": "Device APIs Requirements",
                            "shortlink": "https://www.w3.org/TR/dap-api-reqs/",
                            "description": "ignored",
                            "_links": {
                                "self": {
                                    "href": "https://api.w3.org/specifications/dap-api-reqs"
                                }
                            },
                        },
                        {
                            "shortname": "unsafe",
                            "title": "Unsafe URL",
                            "shortlink": "https://evil.example/specification",
                            "_links": {},
                        },
                    ]
                }
            }
        else:
            raise AssertionError(f"unexpected request: {request.url}")
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json=payload,
            request=request,
        )

    batch = _collect(
        W3cStandardAdapter(
            _entry(),
            (_target(),),
            transport=httpx.MockTransport(handler),
        )
    )

    assert [request.url.path for request in requests] == [
        "/affiliations/1015",
        "/affiliations/1015/participations",
        "/groups/wg/das/specifications",
    ]
    assert requests[1].url.params["items"] == "20"
    assert requests[1].url.params["embed"] == "1"
    assert requests[2].url.params["items"] == "20"
    assert requests[2].url.params["embed"] == "1"
    assert all("participants" not in request.url.path for request in requests)
    assert len(batch.observations) == 1
    assert len(batch.public_footprint_projections) == 1
    projection = batch.public_footprint_projections[0]
    assert projection.claims == ()
    assert projection.resource.canonical_url == "https://www.w3.org/TR/dap-api-reqs/"
    assert projection.resource.retrieval_state.value == "quarantined"
    excerpt = projection.version.excerpt or ""
    assert "wg/das" in excerpt
    assert "Participants, editors, versions and specification body were not retrieved" in excerpt


def test_w3c_identity_mismatch_stops_before_participations() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) > 1:
            raise AssertionError("identity mismatch must stop secondary traversal")
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"id": 1015, "name": "Different Organization"},
            request=request,
        )

    adapter = W3cStandardAdapter(
        _entry(),
        (_target(),),
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(AdapterExecutionError) as exc_info:
        _collect(adapter)
    assert exc_info.value.error_code == "target_identity_mismatch"
    assert exc_info.value.retryable is False
    assert len(requests) == 1


def test_w3c_checkpoint_schema_and_rate_limit_fail_closed() -> None:
    adapter = W3cStandardAdapter(
        _entry(),
        (_target(),),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, request=request)),
    )
    with pytest.raises(AdapterExecutionError) as checkpoint_info:
        _collect(adapter, checkpoint_payload={"target_index": True})
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
            W3cStandardAdapter(
                _entry(),
                (_target(),),
                transport=httpx.MockTransport(malformed),
            )
        )
    assert schema_info.value.error_code == "source_schema_drift"
    assert schema_info.value.retryable is False

    def rate_limited(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"content-type": "application/json"}, request=request)

    with pytest.raises(AdapterExecutionError) as rate_info:
        _collect(
            W3cStandardAdapter(
                _entry(),
                (_target(),),
                transport=httpx.MockTransport(rate_limited),
            )
        )
    assert rate_info.value.error_code == "http_429"
    assert rate_info.value.retryable is True


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(POLICY_PATH)
        if entry.policy.id == "w3c-affiliation-specification-metadata"
    )


def _target(*, enabled: bool = True) -> W3cAffiliationTarget:
    return W3cAffiliationTarget(
        target_id="lbnl-live",
        organization_id=ORG_ID,
        canonical_name=AFFILIATION_NAME,
        affiliation_id=1015,
        enabled=enabled,
    )


def _collect(
    adapter: W3cStandardAdapter,
    *,
    checkpoint_payload: dict[str, object] | None = None,
):
    return adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=checkpoint_payload,
        collected_at=NOW,
        retention_until=RETENTION,
    )

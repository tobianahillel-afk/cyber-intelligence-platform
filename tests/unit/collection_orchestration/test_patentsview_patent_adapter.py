from __future__ import annotations

from datetime import UTC, datetime, timedelta
from json import loads
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest

from cip.adapters.sources.patentsview_patents.registry import (
    PatentsViewPatentTarget,
    load_patentsview_patent_targets,
)
from cip.modules.collection_orchestration.application.patentsview_patent_adapter import (
    PatentsViewPatentAdapter,
)
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 11, 13, 30, tzinfo=UTC)
RETENTION = NOW + timedelta(days=365)
ORG_ID = UUID("0fe0ab6c-1da4-5af0-9089-a9885ac2f3f3")
POLICY_PATH = Path("policies/sources.search_archives.yml")
TARGET_PATH = Path("policies/patentsview_patent_targets.yml")


def test_checked_in_patentsview_registry_is_empty() -> None:
    assert load_patentsview_patent_targets(TARGET_PATH) == ()


def test_patentsview_without_enabled_target_performs_no_network_or_secret_read() -> None:
    secret_reads: list[int] = []

    def token_provider() -> str | None:
        secret_reads.append(1)
        return "api-key"

    def fail_network(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be used without enabled target")

    adapter = PatentsViewPatentAdapter(
        _entry(),
        (_target(enabled=False),),
        token_provider=token_provider,
        transport=httpx.MockTransport(fail_network),
    )
    batch = _collect(adapter)
    assert batch.not_modified is True
    assert batch.observations == ()
    assert secret_reads == []


def test_patentsview_requires_connected_api_key_before_network() -> None:
    def fail_network(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be used without provider key")

    adapter = PatentsViewPatentAdapter(
        _entry(),
        (_target(),),
        token_provider=lambda: None,
        transport=httpx.MockTransport(fail_network),
    )
    with pytest.raises(AdapterExecutionError) as exc_info:
        _collect(adapter)
    assert exc_info.value.error_code == "provider_not_connected"
    assert exc_info.value.retryable is False


def test_patentsview_maps_only_exact_assignee_minimal_metadata() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={
                "error": False,
                "count": 4,
                "total_hits": 4,
                "patents": [
                    _patent("12345678", "Security invention", "Example Corporation"),
                    _patent("12345679", "Other assignee", "Other Corporation"),
                    _patent("bad id", "Bad id", "Example Corporation"),
                    _patent(
                        "12345680",
                        "Bad date",
                        "Example Corporation",
                        patent_date="2026-99-99",
                    ),
                ],
            },
            request=request,
        )

    adapter = PatentsViewPatentAdapter(
        _entry(),
        (_target(),),
        token_provider=lambda: "live-key",
        transport=httpx.MockTransport(handler),
    )
    batch = _collect(adapter)

    assert len(requests) == 1
    request = requests[0]
    assert request.url.path == "/api/v1/patent/"
    assert request.headers["X-Api-Key"] == "live-key"
    assert loads(request.url.params["q"]) == {
        "assignees.assignee_organization": "Example Corporation"
    }
    assert loads(request.url.params["o"]) == {"size": 20}
    fields = loads(request.url.params["f"])
    assert "patent_abstract" not in fields
    assert "inventors" not in fields
    assert "patent_id" in fields
    assert "assignees.assignee_organization" in fields

    assert len(batch.observations) == 1
    assert len(batch.public_footprint_projections) == 1
    projection = batch.public_footprint_projections[0]
    assert projection.claims == ()
    assert projection.resource.retrieval_state.value == "quarantined"
    excerpt = projection.version.excerpt or ""
    assert "Example Corporation" in excerpt
    assert "Abstract, claims, inventors and full text not retrieved" in excerpt
    assert batch.checkpoint_payload == {"target_index": 0}


def test_patentsview_rejects_invalid_checkpoint() -> None:
    adapter = PatentsViewPatentAdapter(
        _entry(),
        (_target(),),
        token_provider=lambda: "key",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, request=request)),
    )
    with pytest.raises(AdapterExecutionError) as exc_info:
        _collect(adapter, checkpoint_payload={"target_index": True})
    assert exc_info.value.error_code == "invalid_checkpoint"


def test_patentsview_classifies_schema_rate_limit_and_error_envelope() -> None:
    def malformed(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b"not-json",
            request=request,
        )

    malformed_adapter = PatentsViewPatentAdapter(
        _entry(),
        (_target(),),
        token_provider=lambda: "key",
        transport=httpx.MockTransport(malformed),
    )
    with pytest.raises(AdapterExecutionError) as schema_info:
        _collect(malformed_adapter)
    assert schema_info.value.error_code == "source_schema_drift"

    def rate_limited(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={"content-type": "application/json"},
            request=request,
        )

    rate_adapter = PatentsViewPatentAdapter(
        _entry(),
        (_target(),),
        token_provider=lambda: "key",
        transport=httpx.MockTransport(rate_limited),
    )
    with pytest.raises(AdapterExecutionError) as rate_info:
        _collect(rate_adapter)
    assert rate_info.value.error_code == "http_429"
    assert rate_info.value.retryable is True

    def provider_error(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"error": True, "count": 0, "total_hits": 0, "patents": []},
            request=request,
        )

    error_adapter = PatentsViewPatentAdapter(
        _entry(),
        (_target(),),
        token_provider=lambda: "key",
        transport=httpx.MockTransport(provider_error),
    )
    with pytest.raises(AdapterExecutionError) as envelope_info:
        _collect(error_adapter)
    assert envelope_info.value.error_code == "source_schema_drift"


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(POLICY_PATH)
        if entry.policy.id == "patentsview-patent-metadata"
    )


def _target(*, enabled: bool = True) -> PatentsViewPatentTarget:
    return PatentsViewPatentTarget(
        target_id="example-patents",
        organization_id=ORG_ID,
        canonical_name="Example Corporation",
        assignee_organization="Example Corporation",
        enabled=enabled,
    )


def _collect(
    adapter: PatentsViewPatentAdapter,
    *,
    checkpoint_payload: dict[str, object] | None = None,
):
    return adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=checkpoint_payload,
        collected_at=NOW,
        retention_until=RETENTION,
    )


def _patent(
    patent_id: str,
    title: str,
    assignee: str,
    *,
    patent_date: str = "2026-06-01",
) -> dict[str, object]:
    return {
        "patent_id": patent_id,
        "patent_title": title,
        "patent_date": patent_date,
        "patent_type": "utility",
        "assignees": [{"assignee_organization": assignee}],
        "patent_abstract": "ignored and never materialized",
        "inventors": [{"inventor_name_first": "ignored"}],
        "claims": [{"claim_text": "ignored"}],
    }

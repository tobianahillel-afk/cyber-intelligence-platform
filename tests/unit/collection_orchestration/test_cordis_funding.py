from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.cordis_funding.client import (
    CordisFundingClient,
    CordisFundingResponseError,
)
from cip.adapters.sources.cordis_funding.collector import (
    CordisFundingCheckpoint,
    CordisFundingCollectionBatch,
    CordisFundingCollectionDeniedError,
    CordisFundingSchemaError,
    collect_cordis_funding,
)
from cip.adapters.sources.cordis_funding.mapper import map_cordis_funding_binding
from cip.adapters.sources.cordis_funding.schemas import CordisFundingBinding
from cip.modules.collection_orchestration.application import (
    cordis_funding_adapter as adapter_module,
)
from cip.modules.collection_orchestration.application.cordis_funding_adapter import (
    CordisFundingAdapter,
)
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 11, 10, 15, tzinfo=UTC)
RETENTION = NOW + timedelta(days=3650)
POLICY_PATH = Path("policies/sources.procurement_funding.yml")


def test_cordis_client_builds_bounded_query_and_accepts_sparql_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        query = request.url.params["query"]
        assert "LIMIT 100" in query
        assert "OFFSET 200" in query
        assert request.headers["Accept"] == "application/sparql-results+json"
        return httpx.Response(
            200,
            headers={"content-type": "application/sparql-results+json"},
            content=_payload(),
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = CordisFundingClient(http_client, endpoint_url=_entry().policy.base_url)
        result = client.fetch_url(client.page_url(200))
    assert result.body == _payload()


def test_cordis_client_rejects_unsafe_content_type_and_size() -> None:
    responses = [
        httpx.Response(200, headers={"content-type": "text/html"}, content=b"x"),
        httpx.Response(
            200,
            headers={
                "content-type": "application/json",
                "content-length": "5000001",
            },
            content=b"{}",
        ),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        response = responses.pop(0)
        return httpx.Response(
            response.status_code,
            headers=response.headers,
            content=response.content,
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = CordisFundingClient(http_client, endpoint_url=_entry().policy.base_url)
        with pytest.raises(CordisFundingResponseError, match="content type"):
            client.fetch_url(client.page_url(0))
        with pytest.raises(CordisFundingResponseError, match="size limit"):
            client.fetch_url(client.page_url(0))


def test_cordis_mapper_preserves_project_level_funding_semantics() -> None:
    binding = _binding()
    observation, claim = map_cordis_funding_binding(
        binding,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=RETENTION,
    )
    assert observation.source_id == "cordis-eu-funded-projects"
    assert observation.source_record_key.startswith("101000001:")
    assert claim.claimed_organization_name == "Example Cyber Research SAS"
    assert claim.organization_id is None
    assert "Project-level maximum EU contribution: 2500000 EUR" in claim.excerpt
    assert "coordinator" in claim.excerpt


def test_cordis_collector_maps_page_and_finishes_on_short_page() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/sparql-results+json"},
            content=_payload(),
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        batch = collect_cordis_funding(
            CordisFundingClient(http_client, endpoint_url=_entry().policy.base_url),
            _entry(),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=RETENTION,
        )
    assert len(batch.observations) == 1
    assert len(batch.claims) == 1
    assert batch.checkpoint is None
    assert batch.not_modified is False


def test_cordis_collector_rejects_schema_drift_and_policy_denial() -> None:
    def invalid_schema(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"unexpected": True},
            request=request,
        )

    with (
        httpx.Client(transport=httpx.MockTransport(invalid_schema)) as http_client,
        pytest.raises(CordisFundingSchemaError),
    ):
        collect_cordis_funding(
            CordisFundingClient(http_client, endpoint_url=_entry().policy.base_url),
            _entry(),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=RETENTION,
        )

    denied = _entry("ademe-financial-aid")
    with (
        httpx.Client(transport=httpx.MockTransport(invalid_schema)) as http_client,
        pytest.raises(CordisFundingCollectionDeniedError),
    ):
        collect_cordis_funding(
            CordisFundingClient(http_client, endpoint_url=denied.policy.base_url),
            denied,
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=RETENTION,
        )


def test_cordis_runtime_adapter_checkpoint_and_failure_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    def fake_collect(*args: object, **kwargs: object) -> CordisFundingCollectionBatch:
        seen["checkpoint"] = kwargs["checkpoint"]
        return CordisFundingCollectionBatch(
            observations=(),
            claims=(),
            checkpoint=CordisFundingCheckpoint(offset=300),
            not_modified=False,
        )

    monkeypatch.setattr(adapter_module, "collect_cordis_funding", fake_collect)
    batch = CordisFundingAdapter(_entry()).collect(
        collection_job_id=uuid4(),
        checkpoint_payload={"offset": 200},
        collected_at=NOW,
        retention_until=RETENTION,
    )
    assert isinstance(seen["checkpoint"], CordisFundingCheckpoint)
    assert batch.checkpoint_payload == {"offset": 300}

    with pytest.raises(AdapterExecutionError) as exc_info:
        CordisFundingAdapter(_entry()).collect(
            collection_job_id=uuid4(),
            checkpoint_payload={"offset": -1},
            collected_at=NOW,
            retention_until=RETENTION,
        )
    assert exc_info.value.error_code == "invalid_checkpoint"


def _binding() -> CordisFundingBinding:
    return CordisFundingBinding.model_validate(
        {
            "project_id": {"type": "literal", "value": "101000001"},
            "project_title": {
                "type": "literal",
                "value": "Cyber resilience research",
                "xml:lang": "en",
            },
            "organisation_name": {
                "type": "literal",
                "value": "Example Cyber Research SAS",
            },
            "role_label": {"type": "literal", "value": "coordinator"},
            "start_date": {
                "type": "literal",
                "value": "2026-01-01",
                "datatype": "http://www.w3.org/2001/XMLSchema#date",
            },
            "end_date": {
                "type": "literal",
                "value": "2028-12-31",
                "datatype": "http://www.w3.org/2001/XMLSchema#date",
            },
            "eu_contribution": {
                "type": "literal",
                "value": "2500000",
                "datatype": "http://www.w3.org/2001/XMLSchema#decimal",
            },
        }
    )


def _payload() -> bytes:
    return json.dumps(
        {
            "head": {
                "vars": [
                    "project_id",
                    "project_title",
                    "organisation_name",
                    "role_label",
                    "start_date",
                    "end_date",
                    "eu_contribution",
                ]
            },
            "results": {
                "bindings": [_binding().model_dump(mode="json", by_alias=True)]
            },
        }
    ).encode()


def _entry(source_id: str = "cordis-eu-funded-projects") -> SourceRegistryEntry:
    return next(
        entry for entry in load_source_registry(POLICY_PATH) if entry.policy.id == source_id
    )

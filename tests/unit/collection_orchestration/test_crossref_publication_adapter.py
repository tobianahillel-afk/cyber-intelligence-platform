from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest

from cip.adapters.sources.crossref_publications.registry import (
    CrossrefPublicationTarget,
    load_crossref_publication_targets,
)
from cip.modules.collection_orchestration.application.crossref_publication_adapter import (
    CrossrefPublicationAdapter,
)
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 11, 13, 0, tzinfo=UTC)
RETENTION = NOW + timedelta(days=180)
ORG_ID = UUID("74b2a087-10ce-5d99-a90c-5aa1c0fabf6f")
POLICY_PATH = Path("policies/sources.search_archives.yml")
TARGET_PATH = Path("policies/crossref_publication_targets.yml")


def test_checked_in_crossref_registry_is_empty() -> None:
    assert load_crossref_publication_targets(TARGET_PATH) == ()


def test_crossref_target_normalizes_ror_url() -> None:
    target = CrossrefPublicationTarget(
        target_id="goethe",
        organization_id=ORG_ID,
        canonical_name="Goethe University Frankfurt",
        ror_id="https://ror.org/04cvxnb49",
        enabled=True,
    )
    assert target.ror_id == "04cvxnb49"


def test_crossref_without_enabled_target_performs_no_network() -> None:
    def fail_network(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be used without enabled target")

    adapter = CrossrefPublicationAdapter(
        _entry(),
        (_target(enabled=False),),
        transport=httpx.MockTransport(fail_network),
    )
    batch = _collect(adapter)
    assert batch.not_modified is True
    assert batch.observations == ()
    assert batch.checkpoint_payload == {"target_index": 0}


def test_crossref_maps_only_minimal_safe_doi_metadata() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={
                "status": "ok",
                "message-type": "work-list",
                "message": {
                    "items": [
                        _work("10.1000/safe", "Useful Research"),
                        _work("10.1000/offhost", "Off host", url="https://example.com/x"),
                        _work("10.1000/untitled", ""),
                    ]
                },
            },
            request=request,
        )

    adapter = CrossrefPublicationAdapter(
        _entry(),
        (_target(),),
        transport=httpx.MockTransport(handler),
    )
    batch = _collect(adapter)

    assert len(requests) == 1
    request = requests[0]
    assert request.url.path == "/works"
    assert request.url.params["filter"] == "ror-id:04cvxnb49"
    assert request.url.params["rows"] == "20"
    assert request.url.params["select"] == "DOI,title,type,URL"
    assert "cyber-intelligence-platform" in request.headers["User-Agent"]

    assert len(batch.observations) == 1
    assert len(batch.public_footprint_projections) == 1
    projection = batch.public_footprint_projections[0]
    assert projection.claims == ()
    assert projection.resource.canonical_url == "https://doi.org/10.1000/safe"
    assert projection.resource.retrieval_state.value == "quarantined"
    excerpt = projection.version.excerpt or ""
    assert "04cvxnb49" in excerpt
    assert "Authors, abstract and full text not retrieved" in excerpt
    assert batch.checkpoint_payload == {"target_index": 0}


def test_crossref_rejects_invalid_checkpoint() -> None:
    adapter = CrossrefPublicationAdapter(
        _entry(),
        (_target(),),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, request=request)),
    )
    with pytest.raises(AdapterExecutionError) as exc_info:
        _collect(adapter, checkpoint_payload={"target_index": True})
    assert exc_info.value.error_code == "invalid_checkpoint"


def test_crossref_classifies_schema_and_rate_limit_failures() -> None:
    def malformed(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b"not-json",
            request=request,
        )

    malformed_adapter = CrossrefPublicationAdapter(
        _entry(),
        (_target(),),
        transport=httpx.MockTransport(malformed),
    )
    with pytest.raises(AdapterExecutionError) as schema_info:
        _collect(malformed_adapter)
    assert schema_info.value.error_code == "source_schema_drift"
    assert schema_info.value.retryable is False

    def rate_limited(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={"content-type": "application/json"},
            request=request,
        )

    rate_adapter = CrossrefPublicationAdapter(
        _entry(),
        (_target(),),
        transport=httpx.MockTransport(rate_limited),
    )
    with pytest.raises(AdapterExecutionError) as rate_info:
        _collect(rate_adapter)
    assert rate_info.value.error_code == "http_429"
    assert rate_info.value.retryable is True


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(POLICY_PATH)
        if entry.policy.id == "crossref-publication-metadata"
    )


def _target(*, enabled: bool = True) -> CrossrefPublicationTarget:
    return CrossrefPublicationTarget(
        target_id="goethe-live",
        organization_id=ORG_ID,
        canonical_name="Goethe University Frankfurt",
        ror_id="04cvxnb49",
        enabled=enabled,
    )


def _collect(
    adapter: CrossrefPublicationAdapter,
    *,
    checkpoint_payload: dict[str, object] | None = None,
):
    return adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=checkpoint_payload,
        collected_at=NOW,
        retention_until=RETENTION,
    )


def _work(
    doi: str,
    title: str,
    *,
    url: str | None = None,
) -> dict[str, object]:
    return {
        "DOI": doi,
        "title": [title],
        "type": "journal-article",
        "URL": url or f"https://doi.org/{doi}",
        "author": [{"given": "ignored", "family": "ignored"}],
        "abstract": "ignored and never materialized",
        "link": [{"URL": "https://publisher.example/fulltext.pdf"}],
    }

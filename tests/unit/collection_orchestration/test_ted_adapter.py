from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.ted_search.client import (
    TedSearchCheckpoint,
    TedSourceResponseError,
)
from cip.adapters.sources.ted_search.collector import (
    TedCollectionBatch,
    TedCollectionDeniedError,
    TedSourceSchemaError,
)
from cip.modules.collection_orchestration.application import ted_adapter as ted_adapter_module
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.collection_orchestration.application.ted_adapter import TedSearchAdapter
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 4, 10, 0, tzinfo=UTC)


def _entry(source_id: str = "ted-search") -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/sources.example.yml"))
        if entry.policy.id == source_id
    )


def test_ted_adapter_maps_checkpoint_and_collection_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_collect(client: object, entry: object, **kwargs: object) -> TedCollectionBatch:
        del client, entry
        captured.update(kwargs)
        return TedCollectionBatch(
            observations=(),
            projections=(),
            buyers=(),
            procurement=(),
            checkpoint=TedSearchCheckpoint(latest_publication_number="300-2026"),
            not_modified=True,
        )

    monkeypatch.setattr(ted_adapter_module, "collect_ted_notices", fake_collect)
    adapter = TedSearchAdapter(_entry())

    batch = adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload={"latest_publication_number": "200-2026"},
        collected_at=NOW,
        retention_until=NOW + timedelta(days=730),
    )

    checkpoint = captured["checkpoint"]
    assert isinstance(checkpoint, TedSearchCheckpoint)
    assert checkpoint.latest_publication_number == "200-2026"
    assert batch.not_modified is True
    assert batch.observations == ()
    assert batch.commercial_projections == ()
    assert batch.procurement_organizations == ()
    assert batch.procurement_projections == ()
    assert batch.checkpoint_payload == {"latest_publication_number": "300-2026"}


def test_ted_adapter_accepts_missing_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_collect(client: object, entry: object, **kwargs: object) -> TedCollectionBatch:
        del client, entry
        captured.update(kwargs)
        return TedCollectionBatch(
            observations=(),
            projections=(),
            buyers=(),
            procurement=(),
            checkpoint=TedSearchCheckpoint(),
            not_modified=False,
        )

    monkeypatch.setattr(ted_adapter_module, "collect_ted_notices", fake_collect)

    TedSearchAdapter(_entry()).collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=NOW,
        retention_until=NOW + timedelta(days=730),
    )

    assert captured["checkpoint"] is None


def test_ted_adapter_validates_constructor_and_checkpoint() -> None:
    with pytest.raises(ValueError, match="ted-search"):
        TedSearchAdapter(_entry("cisa-kev"))
    with pytest.raises(ValueError, match="timeout"):
        TedSearchAdapter(_entry(), timeout_seconds=0)

    with pytest.raises(AdapterExecutionError, match="latest_publication_number") as error:
        TedSearchAdapter(_entry()).collect(
            collection_job_id=uuid4(),
            checkpoint_payload={"latest_publication_number": 42},
            collected_at=NOW,
            retention_until=NOW + timedelta(days=730),
        )

    assert error.value.error_code == "invalid_checkpoint"
    assert error.value.retryable is False


@pytest.mark.parametrize(
    ("exception", "error_code", "retryable"),
    [
        (TedCollectionDeniedError("blocked"), "source_policy_denied", False),
        (TedSourceSchemaError("drift"), "source_schema_drift", False),
        (TedSourceResponseError("unsafe"), "unsafe_source_response", True),
        (httpx.ReadTimeout("timeout"), "source_transport_error", True),
    ],
)
def test_ted_adapter_normalizes_source_errors(
    monkeypatch: pytest.MonkeyPatch,
    exception: Exception,
    error_code: str,
    retryable: bool,
) -> None:
    monkeypatch.setattr(
        ted_adapter_module,
        "collect_ted_notices",
        lambda *args, **kwargs: (_ for _ in ()).throw(exception),
    )

    with pytest.raises(AdapterExecutionError) as error:
        TedSearchAdapter(_entry()).collect(
            collection_job_id=uuid4(),
            checkpoint_payload=None,
            collected_at=NOW,
            retention_until=NOW + timedelta(days=730),
        )

    assert error.value.error_code == error_code
    assert error.value.retryable is retryable


@pytest.mark.parametrize(
    ("status", "retryable"),
    [(404, False), (429, True), (503, True)],
)
def test_ted_adapter_classifies_http_status(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    retryable: bool,
) -> None:
    request = httpx.Request("POST", "https://api.ted.europa.eu/v3/notices/search")
    response = httpx.Response(status, request=request)
    exception = httpx.HTTPStatusError("failure", request=request, response=response)
    monkeypatch.setattr(
        ted_adapter_module,
        "collect_ted_notices",
        lambda *args, **kwargs: (_ for _ in ()).throw(exception),
    )

    with pytest.raises(AdapterExecutionError) as error:
        TedSearchAdapter(_entry()).collect(
            collection_job_id=uuid4(),
            checkpoint_payload=None,
            collected_at=NOW,
            retention_until=NOW + timedelta(days=730),
        )

    assert error.value.error_code == f"http_{status}"
    assert error.value.retryable is retryable

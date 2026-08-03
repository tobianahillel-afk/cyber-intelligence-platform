from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.cisa_kev.client import (
    CisaKevCheckpoint,
    SourceResponseError,
)
from cip.adapters.sources.cisa_kev.collector import (
    CisaKevCollectionBatch,
    CollectionDeniedError,
    SourceSchemaError,
)
from cip.modules.collection_orchestration.application import adapters
from cip.modules.collection_orchestration.application.adapters import CisaKevAdapter
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.source_governance.infrastructure.registry import load_source_registry

NOW = datetime(2026, 8, 3, 18, 30, tzinfo=UTC)


def _entry(source_id: str = "cisa-kev"):
    return next(
        entry
        for entry in load_source_registry(Path("policies/sources.example.yml"))
        if entry.policy.id == source_id
    )


def test_cisa_adapter_maps_checkpoint_and_result(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_collect(client, entry, **kwargs):
        del client, entry
        captured.update(kwargs)
        return CisaKevCollectionBatch(
            observations=(),
            checkpoint=CisaKevCheckpoint(
                etag="new",
                last_modified="later",
                catalog_version="2026.08.03",
            ),
            not_modified=True,
        )

    monkeypatch.setattr(adapters, "collect_cisa_kev", fake_collect)
    adapter = CisaKevAdapter(_entry())
    batch = adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload={
            "etag": "old",
            "last_modified": "earlier",
            "catalog_version": "2026.08.02",
        },
        collected_at=NOW,
        retention_until=NOW + timedelta(days=30),
    )

    checkpoint = captured["checkpoint"]
    assert isinstance(checkpoint, CisaKevCheckpoint)
    assert checkpoint.etag == "old"
    assert batch.not_modified is True
    assert batch.checkpoint_payload["etag"] == "new"


def test_cisa_adapter_validates_constructor_and_checkpoint() -> None:
    with pytest.raises(ValueError, match="cisa-kev"):
        CisaKevAdapter(_entry("brixhub"))
    with pytest.raises(ValueError, match="timeout"):
        CisaKevAdapter(_entry(), timeout_seconds=0)

    adapter = CisaKevAdapter(_entry())
    with pytest.raises(AdapterExecutionError, match="etag") as error:
        adapter.collect(
            collection_job_id=uuid4(),
            checkpoint_payload={"etag": 42},
            collected_at=NOW,
            retention_until=NOW + timedelta(days=30),
        )
    assert error.value.error_code == "invalid_checkpoint"
    assert error.value.retryable is False


@pytest.mark.parametrize(
    ("exception", "error_code", "retryable"),
    [
        (CollectionDeniedError("blocked"), "source_policy_denied", False),
        (SourceSchemaError("drift"), "source_schema_drift", False),
        (SourceResponseError("unsafe"), "unsafe_source_response", True),
        (httpx.ReadTimeout("timeout"), "source_transport_error", True),
    ],
)
def test_cisa_adapter_normalizes_source_errors(
    monkeypatch: pytest.MonkeyPatch,
    exception: Exception,
    error_code: str,
    retryable: bool,
) -> None:
    monkeypatch.setattr(
        adapters,
        "collect_cisa_kev",
        lambda *args, **kwargs: (_ for _ in ()).throw(exception),
    )
    adapter = CisaKevAdapter(_entry())

    with pytest.raises(AdapterExecutionError) as error:
        adapter.collect(
            collection_job_id=uuid4(),
            checkpoint_payload=None,
            collected_at=NOW,
            retention_until=NOW + timedelta(days=30),
        )

    assert error.value.error_code == error_code
    assert error.value.retryable is retryable


@pytest.mark.parametrize(
    ("status", "retryable"),
    [(404, False), (429, True), (503, True)],
)
def test_cisa_adapter_classifies_http_status(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    retryable: bool,
) -> None:
    request = httpx.Request("GET", "https://www.cisa.gov/kev.json")
    response = httpx.Response(status, request=request)
    exception = httpx.HTTPStatusError("failure", request=request, response=response)
    monkeypatch.setattr(
        adapters,
        "collect_cisa_kev",
        lambda *args, **kwargs: (_ for _ in ()).throw(exception),
    )

    with pytest.raises(AdapterExecutionError) as error:
        CisaKevAdapter(_entry()).collect(
            collection_job_id=uuid4(),
            checkpoint_payload=None,
            collected_at=NOW,
            retention_until=NOW + timedelta(days=30),
        )

    assert error.value.error_code == f"http_{status}"
    assert error.value.retryable is retryable

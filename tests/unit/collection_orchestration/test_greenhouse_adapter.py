from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.greenhouse.client import GreenhouseSourceResponseError
from cip.adapters.sources.greenhouse.collector import (
    GreenhouseCheckpoint,
    GreenhouseCollectionBatch,
    GreenhouseCollectionDeniedError,
    GreenhouseSourceSchemaError,
    GreenhouseSourceWindowError,
)
from cip.adapters.sources.greenhouse.registry import GreenhouseBoard
from cip.modules.collection_orchestration.application import greenhouse_adapter as adapter_module
from cip.modules.collection_orchestration.application.greenhouse_adapter import (
    GreenhouseAdapter,
)
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)
BOARD = GreenhouseBoard(
    id="example",
    board_token="example",
    canonical_name="Example Security",
    country_code="FR",
)


def _entry(source_id: str = "greenhouse-job-board") -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/sources.example.yml"))
        if entry.policy.id == source_id
    )


def test_adapter_maps_nested_checkpoint_and_collection_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_collect(
        client: object,
        entry: object,
        boards: object,
        **kwargs: object,
    ) -> GreenhouseCollectionBatch:
        del client, entry, boards
        captured.update(kwargs)
        return GreenhouseCollectionBatch(
            observations=(),
            projections=(),
            checkpoint=GreenhouseCheckpoint(
                {"example": {"123": "new-fingerprint"}}
            ),
            not_modified=True,
        )

    monkeypatch.setattr(adapter_module, "collect_greenhouse_jobs", fake_collect)
    batch = GreenhouseAdapter(_entry(), (BOARD,)).collect(
        collection_job_id=uuid4(),
        checkpoint_payload={"fingerprints": {"example": {"123": "old-fingerprint"}}},
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )

    checkpoint = captured["checkpoint"]
    assert isinstance(checkpoint, GreenhouseCheckpoint)
    assert checkpoint.fingerprints["example"]["123"] == "old-fingerprint"
    assert batch.not_modified is True
    assert batch.commercial_projections == ()
    assert batch.checkpoint_payload == {
        "fingerprints": {"example": {"123": "new-fingerprint"}}
    }


def test_adapter_accepts_missing_checkpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_collect(
        client: object,
        entry: object,
        boards: object,
        **kwargs: object,
    ) -> GreenhouseCollectionBatch:
        del client, entry, boards
        captured.update(kwargs)
        return GreenhouseCollectionBatch((), (), GreenhouseCheckpoint({}), False)

    monkeypatch.setattr(adapter_module, "collect_greenhouse_jobs", fake_collect)
    GreenhouseAdapter(_entry(), (BOARD,)).collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )

    assert captured["checkpoint"] is None


def test_adapter_validates_constructor_and_nested_checkpoint() -> None:
    with pytest.raises(ValueError, match="source policy"):
        GreenhouseAdapter(_entry("cisa-kev"), (BOARD,))
    with pytest.raises(ValueError, match="enabled board"):
        GreenhouseAdapter(_entry(), (GreenhouseBoard("x", "x", "X", enabled=False),))
    with pytest.raises(ValueError, match="timeout"):
        GreenhouseAdapter(_entry(), (BOARD,), timeout_seconds=0)

    invalid_payloads = (
        {},
        {"fingerprints": []},
        {"fingerprints": {1: {}}},
        {"fingerprints": {"example": []}},
        {"fingerprints": {"example": {1: "hash"}}},
        {"fingerprints": {"example": {"123": 42}}},
    )
    for payload in invalid_payloads:
        with pytest.raises(AdapterExecutionError) as error:
            GreenhouseAdapter(_entry(), (BOARD,)).collect(
                collection_job_id=uuid4(),
                checkpoint_payload=payload,
                collected_at=NOW,
                retention_until=NOW + timedelta(days=365),
            )
        assert error.value.error_code == "invalid_checkpoint"
        assert error.value.retryable is False


@pytest.mark.parametrize(
    ("exception", "error_code", "retryable"),
    [
        (GreenhouseCollectionDeniedError("blocked"), "source_policy_denied", False),
        (GreenhouseSourceSchemaError("drift"), "source_schema_drift", False),
        (GreenhouseSourceWindowError("overflow"), "source_window_exceeded", False),
        (GreenhouseSourceResponseError("unsafe"), "unsafe_source_response", True),
        (httpx.ReadTimeout("timeout"), "source_transport_error", True),
    ],
)
def test_adapter_normalizes_source_errors(
    monkeypatch: pytest.MonkeyPatch,
    exception: Exception,
    error_code: str,
    retryable: bool,
) -> None:
    monkeypatch.setattr(
        adapter_module,
        "collect_greenhouse_jobs",
        lambda *args, **kwargs: (_ for _ in ()).throw(exception),
    )

    with pytest.raises(AdapterExecutionError) as error:
        GreenhouseAdapter(_entry(), (BOARD,)).collect(
            collection_job_id=uuid4(),
            checkpoint_payload=None,
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )

    assert error.value.error_code == error_code
    assert error.value.retryable is retryable


@pytest.mark.parametrize(
    ("status", "retryable"),
    [(404, False), (429, True), (503, True)],
)
def test_adapter_classifies_http_status(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    retryable: bool,
) -> None:
    request = httpx.Request("GET", "https://boards-api.greenhouse.io/v1/boards/x/jobs")
    response = httpx.Response(status, request=request)
    exception = httpx.HTTPStatusError("failure", request=request, response=response)
    monkeypatch.setattr(
        adapter_module,
        "collect_greenhouse_jobs",
        lambda *args, **kwargs: (_ for _ in ()).throw(exception),
    )

    with pytest.raises(AdapterExecutionError) as error:
        GreenhouseAdapter(_entry(), (BOARD,)).collect(
            collection_job_id=uuid4(),
            checkpoint_payload=None,
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )

    assert error.value.error_code == f"http_{status}"
    assert error.value.retryable is retryable

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.boamp.client import (
    BoampCheckpoint,
    BoampSourceResponseError,
)
from cip.adapters.sources.boamp.collector import (
    BoampCollectionBatch,
    BoampCollectionDeniedError,
    BoampSourceSchemaError,
    BoampSourceWindowError,
)
from cip.modules.collection_orchestration.application import boamp_adapter as adapter_module
from cip.modules.collection_orchestration.application.boamp_adapter import BoampAdapter
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 4, 10, 0, tzinfo=UTC)


def _entry(source_id: str = "boamp") -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/sources.example.yml"))
        if entry.policy.id == source_id
    )


def test_boamp_adapter_maps_checkpoint_and_result(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_collect(client: object, entry: object, **kwargs: object) -> BoampCollectionBatch:
        del client, entry
        captured.update(kwargs)
        return BoampCollectionBatch(
            observations=(),
            projections=(),
            checkpoint=BoampCheckpoint(
                latest_idweb="26-new",
                latest_publication_date="2026-08-04",
            ),
            not_modified=True,
        )

    monkeypatch.setattr(adapter_module, "collect_boamp_notices", fake_collect)
    batch = BoampAdapter(_entry()).collect(
        collection_job_id=uuid4(),
        checkpoint_payload={
            "latest_idweb": "26-old",
            "latest_publication_date": "2026-08-03",
        },
        collected_at=NOW,
        retention_until=NOW + timedelta(days=730),
    )

    checkpoint = captured["checkpoint"]
    assert isinstance(checkpoint, BoampCheckpoint)
    assert checkpoint.latest_idweb == "26-old"
    assert batch.not_modified is True
    assert batch.commercial_projections == ()
    assert batch.checkpoint_payload == {
        "latest_idweb": "26-new",
        "latest_publication_date": "2026-08-04",
    }


def test_boamp_adapter_accepts_missing_checkpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_collect(client: object, entry: object, **kwargs: object) -> BoampCollectionBatch:
        del client, entry
        captured.update(kwargs)
        return BoampCollectionBatch((), (), BoampCheckpoint(), False)

    monkeypatch.setattr(adapter_module, "collect_boamp_notices", fake_collect)
    BoampAdapter(_entry()).collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=NOW,
        retention_until=NOW + timedelta(days=730),
    )

    assert captured["checkpoint"] is None


def test_boamp_adapter_validates_constructor_and_checkpoint() -> None:
    with pytest.raises(ValueError, match="boamp"):
        BoampAdapter(_entry("cisa-kev"))
    with pytest.raises(ValueError, match="timeout"):
        BoampAdapter(_entry(), timeout_seconds=0)

    for key in ("latest_idweb", "latest_publication_date"):
        with pytest.raises(AdapterExecutionError, match=key) as error:
            BoampAdapter(_entry()).collect(
                collection_job_id=uuid4(),
                checkpoint_payload={key: 42},
                collected_at=NOW,
                retention_until=NOW + timedelta(days=730),
            )
        assert error.value.error_code == "invalid_checkpoint"
        assert error.value.retryable is False


@pytest.mark.parametrize(
    ("exception", "error_code", "retryable"),
    [
        (BoampCollectionDeniedError("blocked"), "source_policy_denied", False),
        (BoampSourceSchemaError("drift"), "source_schema_drift", False),
        (BoampSourceWindowError("overflow"), "source_window_exceeded", False),
        (BoampSourceResponseError("unsafe"), "unsafe_source_response", True),
        (httpx.ReadTimeout("timeout"), "source_transport_error", True),
    ],
)
def test_boamp_adapter_normalizes_source_errors(
    monkeypatch: pytest.MonkeyPatch,
    exception: Exception,
    error_code: str,
    retryable: bool,
) -> None:
    monkeypatch.setattr(
        adapter_module,
        "collect_boamp_notices",
        lambda *args, **kwargs: (_ for _ in ()).throw(exception),
    )

    with pytest.raises(AdapterExecutionError) as error:
        BoampAdapter(_entry()).collect(
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
def test_boamp_adapter_classifies_http_status(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    retryable: bool,
) -> None:
    request = httpx.Request("GET", "https://boamp.example/records")
    response = httpx.Response(status, request=request)
    exception = httpx.HTTPStatusError("failure", request=request, response=response)
    monkeypatch.setattr(
        adapter_module,
        "collect_boamp_notices",
        lambda *args, **kwargs: (_ for _ in ()).throw(exception),
    )

    with pytest.raises(AdapterExecutionError) as error:
        BoampAdapter(_entry()).collect(
            collection_job_id=uuid4(),
            checkpoint_payload=None,
            collected_at=NOW,
            retention_until=NOW + timedelta(days=730),
        )

    assert error.value.error_code == f"http_{status}"
    assert error.value.retryable is retryable

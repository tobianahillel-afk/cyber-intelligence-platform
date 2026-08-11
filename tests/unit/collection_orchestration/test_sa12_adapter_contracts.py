from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.ademe_funding.client import AdemeFundingResponseError
from cip.adapters.sources.ademe_funding.collector import (
    AdemeFundingCheckpoint,
    AdemeFundingCollectionBatch,
    AdemeFundingCollectionDeniedError,
    AdemeFundingPaginationError,
    AdemeFundingSchemaError,
)
from cip.adapters.sources.place_awards.client import PlaceSourceResponseError
from cip.adapters.sources.place_awards.collector import (
    PlaceCheckpoint,
    PlaceCollectionBatch,
    PlaceCollectionDeniedError,
    PlaceSourceSchemaError,
    PlaceSourceWindowError,
)
from cip.modules.collection_orchestration.application import (
    ademe_funding_adapter as ademe_module,
)
from cip.modules.collection_orchestration.application import (
    place_awards_adapter as place_module,
)
from cip.modules.collection_orchestration.application.ademe_funding_adapter import (
    AdemeFundingAdapter,
)
from cip.modules.collection_orchestration.application.place_awards_adapter import (
    PlaceAwardsAdapter,
)
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 11, 8, 30, tzinfo=UTC)
RETENTION = NOW + timedelta(days=365)
POLICY_PATH = Path("policies/sources.procurement_funding.yml")


def test_place_adapter_success_hydrates_checkpoint_and_returns_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = PlaceCollectionBatch(
        observations=(),
        buyers=(),
        procurement=(),
        checkpoint=PlaceCheckpoint("new-key", "2026-08-10"),
        not_modified=False,
    )
    seen: dict[str, object] = {}

    def fake_collect(*args: object, **kwargs: object) -> PlaceCollectionBatch:
        seen["checkpoint"] = kwargs["checkpoint"]
        return expected

    monkeypatch.setattr(place_module, "collect_place_awards", fake_collect)
    batch = PlaceAwardsAdapter(_entry("place-awards")).collect(
        collection_job_id=uuid4(),
        checkpoint_payload={
            "latest_source_record_key": "old-key",
            "latest_notification_date": "2026-08-01",
        },
        collected_at=NOW,
        retention_until=RETENTION,
    )

    checkpoint = seen["checkpoint"]
    assert isinstance(checkpoint, PlaceCheckpoint)
    assert checkpoint.latest_source_record_key == "old-key"
    assert batch.checkpoint_payload == {
        "latest_source_record_key": "new-key",
        "latest_notification_date": "2026-08-10",
    }
    assert batch.not_modified is False


def test_ademe_adapter_success_hydrates_checkpoint_and_returns_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = AdemeFundingCollectionBatch(
        observations=(),
        claims=(),
        checkpoint=AdemeFundingCheckpoint("https://data.ademe.fr/next"),
        not_modified=False,
    )
    seen: dict[str, object] = {}

    def fake_collect(*args: object, **kwargs: object) -> AdemeFundingCollectionBatch:
        seen["checkpoint"] = kwargs["checkpoint"]
        return expected

    monkeypatch.setattr(ademe_module, "collect_ademe_funding", fake_collect)
    batch = AdemeFundingAdapter(_entry("ademe-financial-aid")).collect(
        collection_job_id=uuid4(),
        checkpoint_payload={"next_url": "https://data.ademe.fr/old"},
        collected_at=NOW,
        retention_until=RETENTION,
    )

    checkpoint = seen["checkpoint"]
    assert isinstance(checkpoint, AdemeFundingCheckpoint)
    assert checkpoint.next_url == "https://data.ademe.fr/old"
    assert batch.checkpoint_payload == {"next_url": "https://data.ademe.fr/next"}
    assert batch.corporate_change_claims == ()


@pytest.mark.parametrize(
    ("factory", "expected_code", "retryable"),
    [
        (lambda: PlaceCollectionDeniedError("denied"), "source_policy_denied", False),
        (lambda: PlaceSourceSchemaError("drift"), "source_schema_drift", False),
        (lambda: PlaceSourceWindowError("window"), "source_window_exceeded", False),
        (lambda: PlaceSourceResponseError("unsafe"), "unsafe_source_response", True),
        (lambda: httpx.ReadTimeout("timeout"), "source_transport_error", True),
    ],
)
def test_place_adapter_maps_provider_failures(
    monkeypatch: pytest.MonkeyPatch,
    factory: Callable[[], Exception],
    expected_code: str,
    retryable: bool,
) -> None:
    def fail(*args: object, **kwargs: object) -> PlaceCollectionBatch:
        raise factory()

    monkeypatch.setattr(place_module, "collect_place_awards", fail)
    with pytest.raises(AdapterExecutionError) as exc_info:
        _collect_place()
    assert exc_info.value.error_code == expected_code
    assert exc_info.value.retryable is retryable


@pytest.mark.parametrize(
    ("factory", "expected_code", "retryable"),
    [
        (lambda: AdemeFundingCollectionDeniedError("denied"), "source_policy_denied", False),
        (lambda: AdemeFundingSchemaError("drift"), "source_schema_drift", False),
        (lambda: AdemeFundingPaginationError("cursor"), "unsafe_pagination", False),
        (lambda: AdemeFundingResponseError("unsafe"), "unsafe_source_response", True),
        (lambda: httpx.ConnectError("transport"), "source_transport_error", True),
    ],
)
def test_ademe_adapter_maps_provider_failures(
    monkeypatch: pytest.MonkeyPatch,
    factory: Callable[[], Exception],
    expected_code: str,
    retryable: bool,
) -> None:
    def fail(*args: object, **kwargs: object) -> AdemeFundingCollectionBatch:
        raise factory()

    monkeypatch.setattr(ademe_module, "collect_ademe_funding", fail)
    with pytest.raises(AdapterExecutionError) as exc_info:
        _collect_ademe()
    assert exc_info.value.error_code == expected_code
    assert exc_info.value.retryable is retryable


@pytest.mark.parametrize(
    ("status", "retryable"),
    [(400, False), (429, True), (503, True)],
)
def test_place_adapter_maps_http_status(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    retryable: bool,
) -> None:
    error = _http_status_error(status)

    def fail(*args: object, **kwargs: object) -> PlaceCollectionBatch:
        raise error

    monkeypatch.setattr(place_module, "collect_place_awards", fail)
    with pytest.raises(AdapterExecutionError) as exc_info:
        _collect_place()
    assert exc_info.value.error_code == f"http_{status}"
    assert exc_info.value.retryable is retryable


@pytest.mark.parametrize(
    ("status", "retryable"),
    [(404, False), (429, True), (500, True)],
)
def test_ademe_adapter_maps_http_status(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    retryable: bool,
) -> None:
    error = _http_status_error(status)

    def fail(*args: object, **kwargs: object) -> AdemeFundingCollectionBatch:
        raise error

    monkeypatch.setattr(ademe_module, "collect_ademe_funding", fail)
    with pytest.raises(AdapterExecutionError) as exc_info:
        _collect_ademe()
    assert exc_info.value.error_code == f"http_{status}"
    assert exc_info.value.retryable is retryable


def test_adapters_reject_wrong_policy_timeout_and_checkpoint() -> None:
    place_entry = _entry("place-awards")
    ademe_entry = _entry("ademe-financial-aid")

    with pytest.raises(ValueError, match="source policy"):
        PlaceAwardsAdapter(ademe_entry)
    with pytest.raises(ValueError, match="timeout_seconds"):
        PlaceAwardsAdapter(place_entry, timeout_seconds=0)
    with pytest.raises(ValueError, match="source policy"):
        AdemeFundingAdapter(place_entry)
    with pytest.raises(ValueError, match="timeout_seconds"):
        AdemeFundingAdapter(ademe_entry, timeout_seconds=0)

    with pytest.raises(AdapterExecutionError) as place_error:
        PlaceAwardsAdapter(place_entry).collect(
            collection_job_id=uuid4(),
            checkpoint_payload={"latest_source_record_key": 123},
            collected_at=NOW,
            retention_until=RETENTION,
        )
    assert place_error.value.error_code == "invalid_checkpoint"

    with pytest.raises(AdapterExecutionError) as ademe_error:
        AdemeFundingAdapter(ademe_entry).collect(
            collection_job_id=uuid4(),
            checkpoint_payload={"next_url": 123},
            collected_at=NOW,
            retention_until=RETENTION,
        )
    assert ademe_error.value.error_code == "invalid_checkpoint"


def _collect_place() -> object:
    return PlaceAwardsAdapter(_entry("place-awards")).collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=NOW,
        retention_until=RETENTION,
    )


def _collect_ademe() -> object:
    return AdemeFundingAdapter(_entry("ademe-financial-aid")).collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=NOW,
        retention_until=RETENTION,
    )


def _entry(source_id: str) -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(POLICY_PATH)
        if entry.policy.id == source_id
    )


def _http_status_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://provider.example/resource")
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError("status", request=request, response=response)

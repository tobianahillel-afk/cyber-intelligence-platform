from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.lever.client import LeverSourceResponseError
from cip.adapters.sources.lever.collector import (
    LeverCheckpoint,
    LeverCollectionBatch,
    LeverCollectionDeniedError,
    LeverSourceSchemaError,
    LeverSourceWindowError,
)
from cip.adapters.sources.lever.registry import LeverSite
from cip.adapters.sources.smartrecruiters.client import (
    SmartRecruitersSourceResponseError,
)
from cip.adapters.sources.smartrecruiters.collector import (
    SmartRecruitersCheckpoint,
    SmartRecruitersCollectionBatch,
    SmartRecruitersCollectionDeniedError,
    SmartRecruitersSourceSchemaError,
    SmartRecruitersSourceWindowError,
)
from cip.adapters.sources.smartrecruiters.registry import SmartRecruitersCompany
from cip.modules.collection_orchestration.application import lever_adapter as lever_module
from cip.modules.collection_orchestration.application import (
    smartrecruiters_adapter as smart_module,
)
from cip.modules.collection_orchestration.application.lever_adapter import LeverAdapter
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.collection_orchestration.application.smartrecruiters_adapter import (
    SmartRecruitersAdapter,
)
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 4, 14, 0, tzinfo=UTC)
LEVER_SITE = LeverSite("example", "example", "Example Security", "FR")
SMART_COMPANY = SmartRecruitersCompany(
    "example",
    "example",
    "Example Security",
    "FR",
)


def test_lever_adapter_maps_checkpoint_and_result(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_collect(*args: object, **kwargs: object) -> LeverCollectionBatch:
        del args
        captured.update(kwargs)
        return LeverCollectionBatch(
            (),
            (),
            LeverCheckpoint({"example": {"job-1": "new"}}),
            True,
        )

    monkeypatch.setattr(lever_module, "collect_lever_jobs", fake_collect)
    batch = LeverAdapter(_entry("lever-job-board"), (LEVER_SITE,)).collect(
        collection_job_id=uuid4(),
        checkpoint_payload={"fingerprints": {"example": {"job-1": "old"}}},
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )

    checkpoint = captured["checkpoint"]
    assert isinstance(checkpoint, LeverCheckpoint)
    assert checkpoint.fingerprints["example"]["job-1"] == "old"
    assert batch.not_modified is True
    assert batch.checkpoint_payload == {
        "fingerprints": {"example": {"job-1": "new"}}
    }


def test_smart_adapter_maps_checkpoint_and_result(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_collect(*args: object, **kwargs: object) -> SmartRecruitersCollectionBatch:
        del args
        captured.update(kwargs)
        return SmartRecruitersCollectionBatch(
            (),
            (),
            SmartRecruitersCheckpoint({"example": {"job-1": "new"}}),
            False,
        )

    monkeypatch.setattr(smart_module, "collect_smartrecruiters_jobs", fake_collect)
    batch = SmartRecruitersAdapter(
        _entry("smartrecruiters-job-board"),
        (SMART_COMPANY,),
    ).collect(
        collection_job_id=uuid4(),
        checkpoint_payload={"fingerprints": {"example": {"job-1": "old"}}},
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )

    checkpoint = captured["checkpoint"]
    assert isinstance(checkpoint, SmartRecruitersCheckpoint)
    assert checkpoint.fingerprints["example"]["job-1"] == "old"
    assert batch.not_modified is False
    assert batch.checkpoint_payload == {
        "fingerprints": {"example": {"job-1": "new"}}
    }


def test_adapters_accept_missing_checkpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[object] = []

    def fake_lever(*args: object, **kwargs: object) -> LeverCollectionBatch:
        del args
        captured.append(kwargs["checkpoint"])
        return LeverCollectionBatch((), (), LeverCheckpoint({}), False)

    def fake_smart(*args: object, **kwargs: object) -> SmartRecruitersCollectionBatch:
        del args
        captured.append(kwargs["checkpoint"])
        return SmartRecruitersCollectionBatch(
            (),
            (),
            SmartRecruitersCheckpoint({}),
            False,
        )

    monkeypatch.setattr(lever_module, "collect_lever_jobs", fake_lever)
    monkeypatch.setattr(smart_module, "collect_smartrecruiters_jobs", fake_smart)
    LeverAdapter(_entry("lever-job-board"), (LEVER_SITE,)).collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )
    SmartRecruitersAdapter(
        _entry("smartrecruiters-job-board"),
        (SMART_COMPANY,),
    ).collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=NOW,
        retention_until=NOW + timedelta(days=365),
    )

    assert captured == [None, None]


def test_adapters_validate_constructor_and_checkpoint() -> None:
    with pytest.raises(ValueError, match="source policy"):
        LeverAdapter(_entry("cisa-kev"), (LEVER_SITE,))
    with pytest.raises(ValueError, match="enabled site"):
        LeverAdapter(
            _entry("lever-job-board"),
            (LeverSite("x", "x", "X", enabled=False),),
        )
    with pytest.raises(ValueError, match="timeout"):
        LeverAdapter(_entry("lever-job-board"), (LEVER_SITE,), timeout_seconds=0)

    with pytest.raises(ValueError, match="source policy"):
        SmartRecruitersAdapter(_entry("cisa-kev"), (SMART_COMPANY,))
    with pytest.raises(ValueError, match="enabled company"):
        SmartRecruitersAdapter(
            _entry("smartrecruiters-job-board"),
            (SmartRecruitersCompany("x", "x", "X", enabled=False),),
        )
    with pytest.raises(ValueError, match="timeout"):
        SmartRecruitersAdapter(
            _entry("smartrecruiters-job-board"),
            (SMART_COMPANY,),
            timeout_seconds=0,
        )

    invalid_payloads = (
        {},
        {"fingerprints": []},
        {"fingerprints": {1: {}}},
        {"fingerprints": {"example": []}},
        {"fingerprints": {"example": {1: "hash"}}},
        {"fingerprints": {"example": {"job-1": 42}}},
    )
    for payload in invalid_payloads:
        for adapter in (
            LeverAdapter(_entry("lever-job-board"), (LEVER_SITE,)),
            SmartRecruitersAdapter(
                _entry("smartrecruiters-job-board"),
                (SMART_COMPANY,),
            ),
        ):
            with pytest.raises(AdapterExecutionError) as error:
                adapter.collect(
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
        (LeverCollectionDeniedError("blocked"), "source_policy_denied", False),
        (LeverSourceSchemaError("drift"), "source_schema_drift", False),
        (LeverSourceWindowError("overflow"), "source_window_exceeded", False),
        (LeverSourceResponseError("unsafe"), "unsafe_source_response", True),
        (httpx.ReadTimeout("timeout"), "source_transport_error", True),
    ],
)
def test_lever_adapter_normalizes_errors(
    monkeypatch: pytest.MonkeyPatch,
    exception: Exception,
    error_code: str,
    retryable: bool,
) -> None:
    monkeypatch.setattr(
        lever_module,
        "collect_lever_jobs",
        lambda *args, **kwargs: (_ for _ in ()).throw(exception),
    )
    with pytest.raises(AdapterExecutionError) as error:
        LeverAdapter(_entry("lever-job-board"), (LEVER_SITE,)).collect(
            collection_job_id=uuid4(),
            checkpoint_payload=None,
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )
    assert error.value.error_code == error_code
    assert error.value.retryable is retryable


@pytest.mark.parametrize(
    ("exception", "error_code", "retryable"),
    [
        (
            SmartRecruitersCollectionDeniedError("blocked"),
            "source_policy_denied",
            False,
        ),
        (SmartRecruitersSourceSchemaError("drift"), "source_schema_drift", False),
        (
            SmartRecruitersSourceWindowError("overflow"),
            "source_window_exceeded",
            False,
        ),
        (
            SmartRecruitersSourceResponseError("unsafe"),
            "unsafe_source_response",
            True,
        ),
        (httpx.ReadTimeout("timeout"), "source_transport_error", True),
    ],
)
def test_smart_adapter_normalizes_errors(
    monkeypatch: pytest.MonkeyPatch,
    exception: Exception,
    error_code: str,
    retryable: bool,
) -> None:
    monkeypatch.setattr(
        smart_module,
        "collect_smartrecruiters_jobs",
        lambda *args, **kwargs: (_ for _ in ()).throw(exception),
    )
    with pytest.raises(AdapterExecutionError) as error:
        SmartRecruitersAdapter(
            _entry("smartrecruiters-job-board"),
            (SMART_COMPANY,),
        ).collect(
            collection_job_id=uuid4(),
            checkpoint_payload=None,
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )
    assert error.value.error_code == error_code
    assert error.value.retryable is retryable


@pytest.mark.parametrize(("status", "retryable"), [(404, False), (429, True), (503, True)])
def test_adapters_classify_http_status(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    retryable: bool,
) -> None:
    request = httpx.Request("GET", "https://example.test/jobs")
    response = httpx.Response(status, request=request)
    exception = httpx.HTTPStatusError("failure", request=request, response=response)

    for module, adapter in (
        (
            lever_module,
            LeverAdapter(_entry("lever-job-board"), (LEVER_SITE,)),
        ),
        (
            smart_module,
            SmartRecruitersAdapter(
                _entry("smartrecruiters-job-board"),
                (SMART_COMPANY,),
            ),
        ),
    ):
        attribute = (
            "collect_lever_jobs"
            if module is lever_module
            else "collect_smartrecruiters_jobs"
        )
        monkeypatch.setattr(
            module,
            attribute,
            lambda *args, **kwargs: (_ for _ in ()).throw(exception),
        )
        with pytest.raises(AdapterExecutionError) as error:
            adapter.collect(
                collection_job_id=uuid4(),
                checkpoint_payload=None,
                collected_at=NOW,
                retention_until=NOW + timedelta(days=365),
            )
        assert error.value.error_code == f"http_{status}"
        assert error.value.retryable is retryable


def _entry(source_id: str) -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/sources.example.yml"))
        if entry.policy.id == source_id
    )

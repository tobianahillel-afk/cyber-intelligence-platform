from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest

from cip.adapters.sources.ashby.client import AshbySourceResponseError
from cip.adapters.sources.ashby.collector import (
    AshbyCheckpoint,
    AshbyCollectionBatch,
    AshbyCollectionDeniedError,
    AshbySourceSchemaError,
    AshbySourceWindowError,
)
from cip.adapters.sources.ashby.registry import AshbyBoard
from cip.adapters.sources.recruitee.client import RecruiteeSourceResponseError
from cip.adapters.sources.recruitee.collector import (
    RecruiteeCheckpoint,
    RecruiteeCollectionBatch,
    RecruiteeCollectionDeniedError,
    RecruiteeSourceSchemaError,
    RecruiteeSourceWindowError,
)
from cip.adapters.sources.recruitee.registry import RecruiteeCareerSite
from cip.adapters.sources.teamtailor.client import TeamtailorSourceResponseError
from cip.adapters.sources.teamtailor.collector import (
    TeamtailorCheckpoint,
    TeamtailorCollectionBatch,
    TeamtailorCollectionDeniedError,
    TeamtailorSourceSchemaError,
    TeamtailorSourceWindowError,
)
from cip.adapters.sources.teamtailor.registry import TeamtailorAccount
from cip.modules.collection_orchestration.application import (
    ashby_adapter as ashby_module,
)
from cip.modules.collection_orchestration.application import (
    recruitee_adapter as recruitee_module,
)
from cip.modules.collection_orchestration.application import (
    teamtailor_adapter as teamtailor_module,
)
from cip.modules.collection_orchestration.application.ashby_adapter import AshbyAdapter
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.collection_orchestration.application.recruitee_adapter import RecruiteeAdapter
from cip.modules.collection_orchestration.application.teamtailor_adapter import TeamtailorAdapter
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 11, 0, 45, tzinfo=UTC)
RETENTION = NOW + timedelta(days=365)
ASHBY_BOARD = AshbyBoard("ashby", "Ashby", "Ashby", "US")
RECRUITEE_SITE = RecruiteeCareerSite(
    "people-for-people",
    "peopleforpeople",
    "People for People",
    "NL",
)
TEAMTAILOR_ACCOUNT = TeamtailorAccount(
    id="example",
    canonical_name="Example",
    enabled=True,
)


def test_ashby_adapter_success_hydrates_and_serializes_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = AshbyAdapter(_entry("ashby-job-board"), (ASHBY_BOARD,))
    seen: dict[str, object] = {}

    def collect(*args: object, **kwargs: object) -> AshbyCollectionBatch:
        seen["checkpoint"] = kwargs["checkpoint"]
        return AshbyCollectionBatch(
            observations=(),
            projections=(),
            checkpoint=AshbyCheckpoint({"ashby": {"job-1": "hash"}}),
            not_modified=True,
        )

    monkeypatch.setattr(ashby_module, "collect_ashby_jobs", collect)
    result = adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload={"fingerprints": {"ashby": {"old": "old-hash"}}},
        collected_at=NOW,
        retention_until=RETENTION,
    )

    assert isinstance(seen["checkpoint"], AshbyCheckpoint)
    assert result.not_modified is True
    assert result.checkpoint_payload == {
        "fingerprints": {"ashby": {"job-1": "hash"}}
    }


@pytest.mark.parametrize(
    ("error", "code", "retryable"),
    [
        (AshbyCollectionDeniedError("denied"), "source_policy_denied", False),
        (AshbySourceSchemaError("schema"), "source_schema_drift", False),
        (AshbySourceWindowError("window"), "source_window_exceeded", False),
        (AshbySourceResponseError("response"), "unsafe_source_response", True),
    ],
)
def test_ashby_adapter_maps_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    code: str,
    retryable: bool,
) -> None:
    adapter = AshbyAdapter(_entry("ashby-job-board"), (ASHBY_BOARD,))
    _raise_from_collector(monkeypatch, ashby_module, "collect_ashby_jobs", error)

    with pytest.raises(AdapterExecutionError) as exc:
        _collect(adapter)
    assert exc.value.error_code == code
    assert exc.value.retryable is retryable


def test_ashby_adapter_rejects_invalid_checkpoint_and_configuration() -> None:
    entry = _entry("ashby-job-board")
    adapter = AshbyAdapter(entry, (ASHBY_BOARD,))
    with pytest.raises(AdapterExecutionError, match="checkpoint fingerprints"):
        _collect(adapter, {"fingerprints": {"ashby": {"job": 1}}})
    with pytest.raises(ValueError, match="enabled board"):
        AshbyAdapter(entry, (AshbyBoard("x", "X", "X", enabled=False),))
    with pytest.raises(ValueError, match="timeout_seconds"):
        AshbyAdapter(entry, (ASHBY_BOARD,), timeout_seconds=0)


def test_recruitee_adapter_success_hydrates_and_serializes_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = RecruiteeAdapter(
        _entry("recruitee-careers-site"),
        (RECRUITEE_SITE,),
    )
    seen: dict[str, object] = {}

    def collect(*args: object, **kwargs: object) -> RecruiteeCollectionBatch:
        seen["checkpoint"] = kwargs["checkpoint"]
        return RecruiteeCollectionBatch(
            observations=(),
            projections=(),
            checkpoint=RecruiteeCheckpoint(
                {"people-for-people": {"offer-1": "hash"}}
            ),
            not_modified=False,
        )

    monkeypatch.setattr(recruitee_module, "collect_recruitee_jobs", collect)
    result = adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload={
            "fingerprints": {"people-for-people": {"old": "old-hash"}}
        },
        collected_at=NOW,
        retention_until=RETENTION,
    )

    assert isinstance(seen["checkpoint"], RecruiteeCheckpoint)
    assert result.not_modified is False
    assert result.checkpoint_payload == {
        "fingerprints": {"people-for-people": {"offer-1": "hash"}}
    }


@pytest.mark.parametrize(
    ("error", "code", "retryable"),
    [
        (RecruiteeCollectionDeniedError("denied"), "source_policy_denied", False),
        (RecruiteeSourceSchemaError("schema"), "source_schema_drift", False),
        (RecruiteeSourceWindowError("window"), "source_window_exceeded", False),
        (RecruiteeSourceResponseError("response"), "unsafe_source_response", True),
    ],
)
def test_recruitee_adapter_maps_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    code: str,
    retryable: bool,
) -> None:
    adapter = RecruiteeAdapter(
        _entry("recruitee-careers-site"),
        (RECRUITEE_SITE,),
    )
    _raise_from_collector(monkeypatch, recruitee_module, "collect_recruitee_jobs", error)

    with pytest.raises(AdapterExecutionError) as exc:
        _collect(adapter)
    assert exc.value.error_code == code
    assert exc.value.retryable is retryable


def test_recruitee_adapter_rejects_invalid_checkpoint_and_configuration() -> None:
    entry = _entry("recruitee-careers-site")
    adapter = RecruiteeAdapter(entry, (RECRUITEE_SITE,))
    with pytest.raises(AdapterExecutionError, match="checkpoint fingerprints"):
        _collect(adapter, {"fingerprints": {"site": {"job": 1}}})
    with pytest.raises(ValueError, match="enabled site"):
        RecruiteeAdapter(
            entry,
            (
                RecruiteeCareerSite(
                    "x",
                    "x",
                    "X",
                    enabled=False,
                ),
            ),
        )


def test_teamtailor_adapter_success_hydrates_and_serializes_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = TeamtailorAdapter(
        _entry("teamtailor-public-jobs"),
        TEAMTAILOR_ACCOUNT,
        lambda: "public-read-token",
    )
    seen: dict[str, object] = {}

    def collect(*args: object, **kwargs: object) -> TeamtailorCollectionBatch:
        seen["token"] = kwargs["api_token"]
        seen["checkpoint"] = kwargs["checkpoint"]
        return TeamtailorCollectionBatch(
            observations=(),
            projections=(),
            checkpoint=TeamtailorCheckpoint({"example": {"job-1": "hash"}}),
            not_modified=True,
        )

    monkeypatch.setattr(teamtailor_module, "collect_teamtailor_jobs", collect)
    result = adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload={"fingerprints": {"example": {"old": "old-hash"}}},
        collected_at=NOW,
        retention_until=RETENTION,
    )

    assert seen["token"] == "public-read-token"
    assert isinstance(seen["checkpoint"], TeamtailorCheckpoint)
    assert result.not_modified is True
    assert result.checkpoint_payload == {
        "fingerprints": {"example": {"job-1": "hash"}}
    }


@pytest.mark.parametrize(
    ("error", "code", "retryable"),
    [
        (TeamtailorCollectionDeniedError("denied"), "source_policy_denied", False),
        (TeamtailorSourceSchemaError("schema"), "source_schema_drift", False),
        (TeamtailorSourceWindowError("window"), "source_window_exceeded", False),
        (TeamtailorSourceResponseError("response"), "unsafe_source_response", True),
    ],
)
def test_teamtailor_adapter_maps_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    code: str,
    retryable: bool,
) -> None:
    adapter = TeamtailorAdapter(
        _entry("teamtailor-public-jobs"),
        TEAMTAILOR_ACCOUNT,
        lambda: "token",
    )
    _raise_from_collector(
        monkeypatch,
        teamtailor_module,
        "collect_teamtailor_jobs",
        error,
    )

    with pytest.raises(AdapterExecutionError) as exc:
        _collect(adapter)
    assert exc.value.error_code == code
    assert exc.value.retryable is retryable


def test_teamtailor_adapter_rejects_invalid_checkpoint_and_configuration() -> None:
    entry = _entry("teamtailor-public-jobs")
    adapter = TeamtailorAdapter(entry, TEAMTAILOR_ACCOUNT, lambda: "token")
    with pytest.raises(AdapterExecutionError, match="checkpoint fingerprints"):
        _collect(adapter, {"fingerprints": {"account": {"job": 1}}})
    with pytest.raises(ValueError, match="enabled account"):
        TeamtailorAdapter(
            entry,
            TeamtailorAccount("x", "X", enabled=False),
            lambda: "token",
        )
    with pytest.raises(ValueError, match="timeout_seconds"):
        TeamtailorAdapter(entry, TEAMTAILOR_ACCOUNT, lambda: "token", timeout_seconds=0)


def _collect(
    adapter: AshbyAdapter | RecruiteeAdapter | TeamtailorAdapter,
    checkpoint: dict[str, object] | None = None,
) -> object:
    return adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=checkpoint,
        collected_at=NOW,
        retention_until=RETENTION,
    )


def _entry(source_id: str) -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(Path("policies/sources.ats_expansion.yml"))
        if entry.policy.id == source_id
    )


def _raise_from_collector(
    monkeypatch: pytest.MonkeyPatch,
    module: ModuleType,
    name: str,
    error: Exception,
) -> None:
    def fail(*args: object, **kwargs: object) -> object:
        raise error

    monkeypatch.setattr(module, name, fail)

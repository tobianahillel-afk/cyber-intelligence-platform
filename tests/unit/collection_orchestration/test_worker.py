from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session, sessionmaker

from cip.modules.collection_orchestration.application import worker
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
    ClaimedJob,
    CollectionAdapter,
)
from cip.modules.collection_orchestration.application.worker import WorkerStatus
from cip.modules.collection_orchestration.domain.models import JobStatus
from cip.modules.collection_orchestration.infrastructure.repository import LeaseLostError
from cip.modules.data_governance.infrastructure.retention_loader import load_retention_policy
from cip.modules.source_governance.domain.models import DataCategory

NOW = datetime(2026, 8, 3, 18, 30, tzinfo=UTC)


class FakeAdapter:
    source_id = "source"
    adapter_id = "adapter"
    data_category = DataCategory.VULNERABILITY_METADATA

    def __init__(
        self,
        result: AdapterCollectionBatch | Exception,
    ) -> None:
        self.result = result
        self.retention_until: datetime | None = None

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch:
        del collection_job_id, checkpoint_payload, collected_at
        self.retention_until = retention_until
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _claimed() -> ClaimedJob:
    return ClaimedJob(
        id=uuid4(),
        source_id="source",
        adapter_id="adapter",
        attempt=1,
        lease_owner="worker",
        lease_expires_at=NOW + timedelta(minutes=2),
        max_attempts=4,
        base_delay_seconds=10,
        max_delay_seconds=60,
        circuit_failure_threshold=3,
        circuit_reset_seconds=90,
        checkpoint_payload={"etag": "old"},
    )


def _factory() -> sessionmaker[Session]:
    return cast(sessionmaker[Session], object())


def _patch_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def fake_scope(factory: object) -> Iterator[object]:
        del factory
        yield object()

    monkeypatch.setattr(worker, "session_scope", fake_scope)
    monkeypatch.setattr(
        worker,
        "source_execution_allowed",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        worker,
        "_record_success_health",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        worker,
        "_record_failure_health",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        worker,
        "record_source_value_event",
        lambda *args, **kwargs: False,
    )


def _retention_policy():
    return load_retention_policy(Path("policies/retention.yml"))


def test_worker_returns_idle_when_no_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_scope(monkeypatch)
    monkeypatch.setattr(worker, "claim_next_job", lambda *args, **kwargs: None)

    outcome = worker.run_worker_once(
        _factory(),
        worker_id="worker",
        adapters={},
        retention_policy=_retention_policy(),
        clock=lambda: NOW,
    )

    assert outcome.status is WorkerStatus.IDLE


@pytest.mark.parametrize(
    ("not_modified", "expected"),
    [(False, WorkerStatus.SUCCEEDED), (True, WorkerStatus.NOT_MODIFIED)],
)
def test_worker_completes_successful_batch(
    monkeypatch: pytest.MonkeyPatch,
    not_modified: bool,
    expected: WorkerStatus,
) -> None:
    _patch_scope(monkeypatch)
    claimed = _claimed()
    adapter = FakeAdapter(AdapterCollectionBatch((), {"etag": "new"}, not_modified))
    monkeypatch.setattr(worker, "claim_next_job", lambda *args, **kwargs: claimed)
    monkeypatch.setattr(worker, "complete_job", lambda *args, **kwargs: 3)

    outcome = worker.run_worker_once(
        _factory(),
        worker_id="worker",
        adapters={("source", "adapter"): cast(CollectionAdapter, adapter)},
        retention_policy=_retention_policy(),
        clock=lambda: NOW,
    )

    assert outcome.status is expected
    assert outcome.observations_written == 3
    assert adapter.retention_until is not None
    assert adapter.retention_until > NOW


def test_worker_dead_letters_missing_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_scope(monkeypatch)
    claimed = _claimed()
    captured: dict[str, object] = {}
    monkeypatch.setattr(worker, "claim_next_job", lambda *args, **kwargs: claimed)

    def fake_fail(*args, **kwargs):
        captured.update(kwargs)
        return JobStatus.DEAD_LETTERED

    monkeypatch.setattr(worker, "fail_job", fake_fail)
    outcome = worker.run_worker_once(
        _factory(),
        worker_id="worker",
        adapters={},
        retention_policy=_retention_policy(),
        clock=lambda: NOW,
    )

    assert outcome.status is WorkerStatus.DEAD_LETTERED
    assert outcome.error_code == "adapter_not_registered"
    assert captured["retryable"] is False


@pytest.mark.parametrize(
    ("exception", "status", "error_code"),
    [
        (
            AdapterExecutionError("temporary", error_code="timeout", retryable=True),
            WorkerStatus.RETRY_SCHEDULED,
            "timeout",
        ),
        (
            AdapterExecutionError("invalid", error_code="schema", retryable=False),
            WorkerStatus.DEAD_LETTERED,
            "schema",
        ),
        (RuntimeError("unexpected"), WorkerStatus.RETRY_SCHEDULED, "unexpected_adapter_error"),
    ],
)
def test_worker_records_adapter_failures(
    monkeypatch: pytest.MonkeyPatch,
    exception: Exception,
    status: WorkerStatus,
    error_code: str,
) -> None:
    _patch_scope(monkeypatch)
    claimed = _claimed()
    adapter = FakeAdapter(exception)
    monkeypatch.setattr(worker, "claim_next_job", lambda *args, **kwargs: claimed)
    monkeypatch.setattr(
        worker,
        "fail_job",
        lambda *args, **kwargs: (
            JobStatus.RETRY_SCHEDULED
            if status is WorkerStatus.RETRY_SCHEDULED
            else JobStatus.DEAD_LETTERED
        ),
    )

    outcome = worker.run_worker_once(
        _factory(),
        worker_id="worker",
        adapters={("source", "adapter"): cast(CollectionAdapter, adapter)},
        retention_policy=_retention_policy(),
        clock=lambda: NOW,
    )

    assert outcome.status is status
    assert outcome.error_code == error_code


def test_worker_reports_lease_loss_on_completion_and_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_scope(monkeypatch)
    claimed = _claimed()
    adapter = FakeAdapter(AdapterCollectionBatch((), {}, False))
    monkeypatch.setattr(worker, "claim_next_job", lambda *args, **kwargs: claimed)
    monkeypatch.setattr(
        worker,
        "complete_job",
        lambda *args, **kwargs: (_ for _ in ()).throw(LeaseLostError("lost")),
    )
    outcome = worker.run_worker_once(
        _factory(),
        worker_id="worker",
        adapters={("source", "adapter"): cast(CollectionAdapter, adapter)},
        retention_policy=_retention_policy(),
        clock=lambda: NOW,
    )
    assert outcome.status is WorkerStatus.LEASE_LOST

    adapter.result = AdapterExecutionError("temporary", error_code="timeout", retryable=True)
    monkeypatch.setattr(
        worker,
        "fail_job",
        lambda *args, **kwargs: (_ for _ in ()).throw(LeaseLostError("lost")),
    )
    outcome = worker.run_worker_once(
        _factory(),
        worker_id="worker",
        adapters={("source", "adapter"): cast(CollectionAdapter, adapter)},
        retention_policy=_retention_policy(),
        clock=lambda: NOW,
    )
    assert outcome.status is WorkerStatus.LEASE_LOST


def test_worker_rejects_naive_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_scope(monkeypatch)

    with pytest.raises(ValueError, match="timezone-aware"):
        worker.run_worker_once(
            _factory(),
            worker_id="worker",
            adapters={},
            retention_policy=_retention_policy(),
            clock=lambda: datetime(2026, 8, 3),
        )

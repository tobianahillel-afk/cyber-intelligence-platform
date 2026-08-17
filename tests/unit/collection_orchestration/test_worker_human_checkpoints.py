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
    ClaimedJob,
    CollectionAdapter,
    HumanCheckpointRequiredError,
)
from cip.modules.collection_orchestration.application.worker import WorkerStatus
from cip.modules.collection_orchestration.domain.human_checkpoints import (
    HumanCheckpointBinding,
    HumanCheckpointKind,
    HumanCheckpointRequest,
)
from cip.modules.collection_orchestration.domain.models import JobStatus
from cip.modules.collection_orchestration.infrastructure.repository import (
    HumanCheckpointConflictError,
    LeaseLostError,
)
from cip.modules.data_governance.infrastructure.retention_loader import load_retention_policy
from cip.modules.source_governance.domain.models import DataCategory

NOW = datetime(2026, 8, 17, 11, 0, tzinfo=UTC)


class CheckpointAdapter:
    source_id = "source"
    adapter_id = "adapter"
    data_category = DataCategory.VULNERABILITY_METADATA

    def __init__(self, checkpoint: HumanCheckpointRequest) -> None:
        self.checkpoint = checkpoint

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch:
        del collection_job_id, checkpoint_payload, collected_at, retention_until
        raise HumanCheckpointRequiredError(self.checkpoint)


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
        checkpoint_payload={"cursor": "before-challenge"},
    )


def _checkpoint(claimed: ClaimedJob) -> HumanCheckpointRequest:
    return HumanCheckpointRequest.from_correlation_token(
        binding=HumanCheckpointBinding(
            job_id=claimed.id,
            source_id=claimed.source_id,
            adapter_id=claimed.adapter_id,
            delegated_identity_id=uuid4(),
            purpose="authenticated-provider-research",
        ),
        kind=HumanCheckpointKind.MFA,
        correlation_token="controlled-worker-resume-token-001",
        session_reference="file-secret:///run/secrets/session.json",
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=15),
    )


def _factory() -> sessionmaker[Session]:
    return cast(sessionmaker[Session], object())


def _retention_policy():
    return load_retention_policy(Path("policies/retention.yml"))


def _patch_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def fake_scope(factory: object) -> Iterator[object]:
        del factory
        yield object()

    monkeypatch.setattr(worker, "session_scope", fake_scope)
    monkeypatch.setattr(worker, "source_execution_allowed", lambda *args, **kwargs: True)
    monkeypatch.setattr(worker, "record_failure_health", lambda *args, **kwargs: None)
    monkeypatch.setattr(worker, "expire_human_checkpoints", lambda *args, **kwargs: 0)


def test_worker_expires_human_checkpoints_before_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_scope(monkeypatch)
    calls: list[datetime] = []
    monkeypatch.setattr(
        worker,
        "expire_human_checkpoints",
        lambda _session, *, now: calls.append(now) or 0,
    )
    monkeypatch.setattr(worker, "claim_next_job", lambda *args, **kwargs: None)

    outcome = worker.run_worker_once(
        _factory(),
        worker_id="worker",
        adapters={},
        retention_policy=_retention_policy(),
        clock=lambda: NOW,
    )

    assert outcome.status is WorkerStatus.IDLE
    assert calls == [NOW]


def test_worker_pauses_legitimate_human_challenge_without_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_scope(monkeypatch)
    claimed = _claimed()
    checkpoint = _checkpoint(claimed)
    captured: dict[str, object] = {}
    monkeypatch.setattr(worker, "claim_next_job", lambda *args, **kwargs: claimed)

    def fake_pause(_session, persisted_claimed, persisted_checkpoint, *, now):
        captured.update(
            claimed=persisted_claimed,
            checkpoint=persisted_checkpoint,
            now=now,
        )
        return persisted_checkpoint.id

    monkeypatch.setattr(worker, "pause_claimed_job_for_human", fake_pause)
    monkeypatch.setattr(
        worker,
        "fail_job",
        lambda *args, **kwargs: pytest.fail("legitimate checkpoint must not fail the job"),
    )
    monkeypatch.setattr(
        worker,
        "record_failure_health",
        lambda *args, **kwargs: pytest.fail("legitimate checkpoint is not source failure"),
    )

    outcome = worker.run_worker_once(
        _factory(),
        worker_id="worker",
        adapters={
            ("source", "adapter"): cast(CollectionAdapter, CheckpointAdapter(checkpoint))
        },
        retention_policy=_retention_policy(),
        clock=lambda: NOW,
    )

    assert outcome.status is WorkerStatus.AWAITING_HUMAN_CHECKPOINT
    assert outcome.job_id == claimed.id
    assert outcome.error_code == "human_checkpoint_required"
    assert captured == {"claimed": claimed, "checkpoint": checkpoint, "now": NOW}


def test_worker_reports_lease_loss_while_persisting_human_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_scope(monkeypatch)
    claimed = _claimed()
    checkpoint = _checkpoint(claimed)
    monkeypatch.setattr(worker, "claim_next_job", lambda *args, **kwargs: claimed)
    monkeypatch.setattr(
        worker,
        "pause_claimed_job_for_human",
        lambda *args, **kwargs: (_ for _ in ()).throw(LeaseLostError("lost")),
    )

    outcome = worker.run_worker_once(
        _factory(),
        worker_id="worker",
        adapters={
            ("source", "adapter"): cast(CollectionAdapter, CheckpointAdapter(checkpoint))
        },
        retention_policy=_retention_policy(),
        clock=lambda: NOW,
    )

    assert outcome.status is WorkerStatus.LEASE_LOST
    assert outcome.error_code == "lease_lost"


def test_invalid_human_checkpoint_is_terminal_adapter_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_scope(monkeypatch)
    claimed = _claimed()
    checkpoint = _checkpoint(claimed)
    captured: dict[str, object] = {}
    monkeypatch.setattr(worker, "claim_next_job", lambda *args, **kwargs: claimed)
    monkeypatch.setattr(
        worker,
        "pause_claimed_job_for_human",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            HumanCheckpointConflictError("binding mismatch")
        ),
    )

    def fake_fail(*args, **kwargs):
        captured.update(kwargs)
        return JobStatus.DEAD_LETTERED

    monkeypatch.setattr(worker, "fail_job", fake_fail)

    outcome = worker.run_worker_once(
        _factory(),
        worker_id="worker",
        adapters={
            ("source", "adapter"): cast(CollectionAdapter, CheckpointAdapter(checkpoint))
        },
        retention_policy=_retention_policy(),
        clock=lambda: NOW,
    )

    assert outcome.status is WorkerStatus.DEAD_LETTERED
    assert outcome.error_code == "invalid_human_checkpoint"
    assert captured["retryable"] is False

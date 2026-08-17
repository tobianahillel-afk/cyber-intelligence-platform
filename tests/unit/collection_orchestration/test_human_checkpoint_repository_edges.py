from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session, sessionmaker

from cip.modules.collection_orchestration.application.ports import ClaimedJob
from cip.modules.collection_orchestration.application.scheduler import schedule_due_jobs
from cip.modules.collection_orchestration.domain.human_checkpoints import (
    HumanCheckpointBinding,
    HumanCheckpointKind,
    HumanCheckpointRequest,
    HumanCheckpointResumeRequest,
)
from cip.modules.collection_orchestration.domain.models import JobStatus, SourceSchedule
from cip.modules.collection_orchestration.infrastructure.models import CollectionJobRecord
from cip.modules.collection_orchestration.infrastructure.repository import (
    HumanCheckpointConflictError,
    HumanCheckpointResumeDeniedError,
    cancel_human_checkpoint,
    claim_next_job,
    expire_human_checkpoints,
    invalidate_human_checkpoints_for_identity,
    pause_claimed_job_for_human,
    resume_human_checkpoint,
)
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 17, 10, 0, tzinfo=UTC)
IDENTITY_ID = UUID("10000000-0000-4000-8000-000000000001")
TOKEN = "controlled-human-correlation-token"


def _factory() -> sessionmaker[Session]:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return create_session_factory(engine)


def _schedule() -> SourceSchedule:
    return SourceSchedule(
        source_id="provider",
        adapter_id="adapter",
        interval_seconds=900,
        lease_seconds=120,
        max_attempts=4,
        base_delay_seconds=30,
        max_delay_seconds=900,
        circuit_failure_threshold=3,
        circuit_reset_seconds=900,
    )


def _claim(session: Session, *, now: datetime = NOW) -> ClaimedJob:
    assert schedule_due_jobs(session, [_schedule()], now=now) == 1
    claimed = claim_next_job(session, worker_id="worker", now=now)
    assert claimed is not None
    return claimed


def _binding(job_id: UUID, **changes: object) -> HumanCheckpointBinding:
    values: dict[str, object] = {
        "job_id": job_id,
        "source_id": "provider",
        "adapter_id": "adapter",
        "delegated_identity_id": IDENTITY_ID,
        "purpose": "authorized-research",
    }
    values.update(changes)
    return HumanCheckpointBinding(**values)  # type: ignore[arg-type]


def _checkpoint(
    job_id: UUID,
    *,
    created_at: datetime = NOW,
    expires_at: datetime | None = None,
    binding: HumanCheckpointBinding | None = None,
) -> HumanCheckpointRequest:
    return HumanCheckpointRequest.from_correlation_token(
        binding=binding or _binding(job_id),
        kind=HumanCheckpointKind.PROVIDER_CHALLENGE,
        correlation_token=TOKEN,
        session_reference="file-secret:///run/secrets/checkpoint.json",
        created_at=created_at,
        expires_at=expires_at or created_at + timedelta(minutes=10),
    )


def _resume(job_id: UUID, checkpoint_id: UUID, *, at: datetime) -> HumanCheckpointResumeRequest:
    return HumanCheckpointResumeRequest(
        checkpoint_id=checkpoint_id,
        binding=_binding(job_id),
        correlation_token=TOKEN,
        actor_reference="user:approver",
        resumed_at=at,
    )


def test_pause_rejects_checkpoint_outside_current_window() -> None:
    factory = _factory()
    with factory.begin() as session:
        claimed = _claim(session)
        future = _checkpoint(
            claimed.id,
            created_at=NOW + timedelta(seconds=1),
        )
        with pytest.raises(ValueError, match="must be current"):
            pause_claimed_job_for_human(session, claimed, future, now=NOW)

        expired = _checkpoint(
            claimed.id,
            created_at=NOW - timedelta(minutes=2),
            expires_at=NOW - timedelta(minutes=1),
        )
        with pytest.raises(ValueError, match="must be current"):
            pause_claimed_job_for_human(session, claimed, expired, now=NOW)


def test_pause_rejects_claim_binding_mismatch() -> None:
    factory = _factory()
    with factory.begin() as session:
        claimed = _claim(session)
        checkpoint = _checkpoint(
            claimed.id,
            binding=_binding(claimed.id, adapter_id="other-adapter"),
        )
        with pytest.raises(HumanCheckpointConflictError, match="does not match"):
            pause_claimed_job_for_human(session, claimed, checkpoint, now=NOW)


def test_resume_rejects_missing_nonwaiting_and_expired_checkpoint() -> None:
    factory = _factory()
    with factory.begin() as session:
        claimed = _claim(session)
        with pytest.raises(HumanCheckpointResumeDeniedError, match="not found"):
            resume_human_checkpoint(
                session,
                _resume(claimed.id, uuid4(), at=NOW),
            )

        checkpoint = _checkpoint(
            claimed.id,
            expires_at=NOW + timedelta(seconds=1),
        )
        pause_claimed_job_for_human(session, claimed, checkpoint, now=NOW)
        with pytest.raises(HumanCheckpointResumeDeniedError, match="expired"):
            resume_human_checkpoint(
                session,
                _resume(claimed.id, checkpoint.id, at=NOW + timedelta(seconds=2)),
            )

        cancel_human_checkpoint(
            session,
            checkpoint_id=checkpoint.id,
            actor_reference="user:operator",
            reason="cancel after expiry assertion",
            now=NOW + timedelta(seconds=3),
        )
        with pytest.raises(HumanCheckpointResumeDeniedError, match="not waiting"):
            resume_human_checkpoint(
                session,
                _resume(claimed.id, checkpoint.id, at=NOW + timedelta(seconds=4)),
            )


def test_resume_rejects_job_state_or_binding_drift() -> None:
    factory = _factory()
    with factory.begin() as session:
        claimed = _claim(session)
        checkpoint = _checkpoint(claimed.id)
        pause_claimed_job_for_human(session, claimed, checkpoint, now=NOW)
        job = session.get(CollectionJobRecord, claimed.id)
        assert job is not None
        job.status = JobStatus.CANCELLED.value
        session.flush()
        with pytest.raises(HumanCheckpointConflictError, match="not awaiting"):
            resume_human_checkpoint(
                session,
                _resume(claimed.id, checkpoint.id, at=NOW + timedelta(seconds=1)),
            )

    factory = _factory()
    with factory.begin() as session:
        claimed = _claim(session)
        checkpoint = _checkpoint(claimed.id)
        pause_claimed_job_for_human(session, claimed, checkpoint, now=NOW)
        job = session.get(CollectionJobRecord, claimed.id)
        assert job is not None
        job.adapter_id = "changed-adapter"
        session.flush()
        with pytest.raises(HumanCheckpointConflictError, match="binding changed"):
            resume_human_checkpoint(
                session,
                _resume(claimed.id, checkpoint.id, at=NOW + timedelta(seconds=1)),
            )


def test_terminal_transitions_handle_noop_and_already_terminal_job() -> None:
    factory = _factory()
    with factory.begin() as session:
        assert expire_human_checkpoints(session, now=NOW) == 0
        assert (
            invalidate_human_checkpoints_for_identity(
                session,
                delegated_identity_id=IDENTITY_ID,
                reason="identity revoked",
                now=NOW,
            )
            == 0
        )

        claimed = _claim(session)
        checkpoint = _checkpoint(claimed.id)
        pause_claimed_job_for_human(session, claimed, checkpoint, now=NOW)
        job = session.get(CollectionJobRecord, claimed.id)
        assert job is not None
        job.status = JobStatus.DEAD_LETTERED.value
        session.flush()
        assert (
            cancel_human_checkpoint(
                session,
                checkpoint_id=checkpoint.id,
                actor_reference="user:operator",
                reason="already terminal",
                now=NOW + timedelta(seconds=1),
            )
            == claimed.id
        )
        assert job.status == JobStatus.DEAD_LETTERED.value


def test_cancel_and_invalidate_reject_invalid_reason() -> None:
    factory = _factory()
    with factory.begin() as session:
        claimed = _claim(session)
        checkpoint = _checkpoint(claimed.id)
        pause_claimed_job_for_human(session, claimed, checkpoint, now=NOW)
        with pytest.raises(ValueError, match="reason"):
            cancel_human_checkpoint(
                session,
                checkpoint_id=checkpoint.id,
                actor_reference="user:operator",
                reason=" ",
                now=NOW + timedelta(seconds=1),
            )
        with pytest.raises(ValueError, match="reason"):
            invalidate_human_checkpoints_for_identity(
                session,
                delegated_identity_id=IDENTITY_ID,
                reason="x" * 501,
                now=NOW + timedelta(seconds=1),
            )

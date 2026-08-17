from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from cip.modules.collection_orchestration.application.scheduler import schedule_due_jobs
from cip.modules.collection_orchestration.domain.human_checkpoints import (
    HumanCheckpointBinding,
    HumanCheckpointKind,
    HumanCheckpointRequest,
    HumanCheckpointResumeRequest,
    HumanCheckpointState,
)
from cip.modules.collection_orchestration.domain.models import JobStatus, SourceSchedule
from cip.modules.collection_orchestration.infrastructure.models import (
    CollectionHumanCheckpointEventRecord,
    CollectionHumanCheckpointRecord,
    CollectionJobRecord,
)
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
from cip.modules.source_governance.infrastructure.delegated_identity_models import (
    DelegatedBrowserIdentityRecord,
)
from cip.modules.source_governance.infrastructure.persistence import sync_source_registry
from cip.modules.source_governance.infrastructure.registry import load_source_registry
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 17, 10, 0, tzinfo=UTC)
IDENTITY_ID = UUID("11111111-1111-4111-8111-111111111111")
TOKEN = "controlled-resume-token-0001"
PURPOSE = "authenticated-provider-research"


def _factory() -> sessionmaker[Session]:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        sync_source_registry(
            session,
            load_source_registry(Path("policies/sources.example.yml")),
        )
        session.add(
            DelegatedBrowserIdentityRecord(
                id=IDENTITY_ID,
                source_id="cisa-kev",
                external_reference="controlled-account",
                auth_mode="interactive_session",
                account_status="active",
                authorization_document_reference="AUTH-L17",
                approved_purposes=[PURPOSE],
                tenant_id=uuid4(),
                owner_kind="service_principal",
                owner_subject_id="l17-worker",
                purpose=PURPOSE,
                approved_scopes=["authenticated-page.read"],
                secret_reference=None,
                session_reference="file-secret:///run/secrets/session.json",
                created_at=NOW,
                verified_at=NOW,
                account_expires_at=NOW + timedelta(days=30),
                last_used_at=None,
                authorized_at=NOW,
                reviewed_at=NOW,
                renewed_at=None,
                reference_rotated_at=None,
                revoked_at=None,
                deleted_at=None,
                session_expires_at=NOW + timedelta(hours=4),
                reference_version=1,
                updated_at=NOW,
            )
        )
    return factory


def _schedule() -> SourceSchedule:
    return SourceSchedule(
        source_id="cisa-kev",
        adapter_id="cisa-kev-feed",
        interval_seconds=900,
        lease_seconds=120,
    )


def _claimed(session: Session):
    assert schedule_due_jobs(session, [_schedule()], now=NOW) == 1
    claimed = claim_next_job(session, worker_id="worker-l17", now=NOW)
    assert claimed is not None
    return claimed


def _binding(job_id: UUID) -> HumanCheckpointBinding:
    return HumanCheckpointBinding(
        job_id=job_id,
        source_id="cisa-kev",
        adapter_id="cisa-kev-feed",
        delegated_identity_id=IDENTITY_ID,
        purpose=PURPOSE,
    )


def _checkpoint(
    job_id: UUID,
    *,
    expires_at: datetime | None = None,
) -> HumanCheckpointRequest:
    return HumanCheckpointRequest.from_correlation_token(
        binding=_binding(job_id),
        kind=HumanCheckpointKind.MFA,
        correlation_token=TOKEN,
        session_reference="file-secret:///run/secrets/session.json",
        created_at=NOW,
        expires_at=expires_at or NOW + timedelta(minutes=15),
    )


def _resume(
    checkpoint_id: UUID,
    job_id: UUID,
    *,
    token: str = TOKEN,
) -> HumanCheckpointResumeRequest:
    return HumanCheckpointResumeRequest(
        checkpoint_id=checkpoint_id,
        binding=_binding(job_id),
        correlation_token=token,
        actor_reference="user:checkpoint-approver",
        resumed_at=NOW + timedelta(minutes=1),
    )


def test_pause_releases_lease_blocks_duplicate_schedule_and_skips_claim() -> None:
    factory = _factory()
    with factory.begin() as session:
        claimed = _claimed(session)
        checkpoint = _checkpoint(claimed.id)

        checkpoint_id = pause_claimed_job_for_human(
            session,
            claimed,
            checkpoint,
            now=NOW,
        )
        job = session.get(CollectionJobRecord, claimed.id)
        persisted = session.get(CollectionHumanCheckpointRecord, checkpoint_id)

        assert job is not None
        assert job.status == JobStatus.AWAITING_HUMAN_CHECKPOINT.value
        assert job.lease_owner is None
        assert job.lease_expires_at is None
        assert persisted is not None
        assert persisted.state == HumanCheckpointState.WAITING.value
        assert TOKEN not in persisted.correlation_digest
        assert schedule_due_jobs(session, [_schedule()], now=NOW + timedelta(hours=1)) == 0
        assert claim_next_job(session, worker_id="other-worker", now=NOW) is None


def test_resume_preserves_same_job_and_does_not_consume_retry_attempt() -> None:
    factory = _factory()
    with factory.begin() as session:
        claimed = _claimed(session)
        checkpoint = _checkpoint(claimed.id)
        pause_claimed_job_for_human(session, claimed, checkpoint, now=NOW)
        original_attempt = claimed.attempt

        resumed_job_id = resume_human_checkpoint(session, _resume(checkpoint.id, claimed.id))
        resumed_record = session.get(CollectionJobRecord, claimed.id)
        persisted = session.get(CollectionHumanCheckpointRecord, checkpoint.id)
        assert resumed_job_id == claimed.id
        assert resumed_record is not None
        assert resumed_record.status == JobStatus.PENDING.value
        assert resumed_record.human_resume_pending
        assert persisted is not None
        assert persisted.state == HumanCheckpointState.COMPLETED.value

        reclaimed = claim_next_job(
            session,
            worker_id="worker-after-restart",
            now=NOW + timedelta(minutes=1),
        )
        assert reclaimed is not None
        assert reclaimed.id == claimed.id
        assert reclaimed.attempt == original_attempt
        assert not resumed_record.human_resume_pending


def test_resume_fails_closed_for_wrong_token_or_binding() -> None:
    factory = _factory()
    with factory.begin() as session:
        claimed = _claimed(session)
        checkpoint = _checkpoint(claimed.id)
        pause_claimed_job_for_human(session, claimed, checkpoint, now=NOW)

        with pytest.raises(HumanCheckpointResumeDeniedError, match="correlation mismatch"):
            resume_human_checkpoint(
                session,
                _resume(
                    checkpoint.id,
                    claimed.id,
                    token="different-resume-token-0002",
                ),
            )
        bad_binding = HumanCheckpointBinding(
            job_id=claimed.id,
            source_id="cisa-kev",
            adapter_id="cisa-kev-feed",
            delegated_identity_id=uuid4(),
            purpose=PURPOSE,
        )
        with pytest.raises(HumanCheckpointResumeDeniedError, match="binding mismatch"):
            resume_human_checkpoint(
                session,
                HumanCheckpointResumeRequest(
                    checkpoint_id=checkpoint.id,
                    binding=bad_binding,
                    correlation_token=TOKEN,
                    actor_reference="user:checkpoint-approver",
                    resumed_at=NOW + timedelta(minutes=1),
                ),
            )
        persisted = session.get(CollectionHumanCheckpointRecord, checkpoint.id)
        assert persisted is not None
        assert persisted.state == HumanCheckpointState.WAITING.value


def test_checkpoint_expiry_cancels_same_job_and_prevents_resume() -> None:
    factory = _factory()
    with factory.begin() as session:
        claimed = _claimed(session)
        checkpoint = _checkpoint(claimed.id, expires_at=NOW + timedelta(seconds=30))
        pause_claimed_job_for_human(session, claimed, checkpoint, now=NOW)

        assert expire_human_checkpoints(session, now=NOW + timedelta(seconds=31)) == 1
        job = session.get(CollectionJobRecord, claimed.id)
        persisted = session.get(CollectionHumanCheckpointRecord, checkpoint.id)
        assert job is not None
        assert job.status == JobStatus.CANCELLED.value
        assert job.error_code == "human_checkpoint_expired"
        assert persisted is not None
        assert persisted.state == HumanCheckpointState.EXPIRED.value
        with pytest.raises(HumanCheckpointResumeDeniedError, match="not waiting"):
            resume_human_checkpoint(session, _resume(checkpoint.id, claimed.id))


def test_checkpoint_cancel_and_identity_invalidation_are_audited() -> None:
    factory = _factory()
    with factory.begin() as session:
        first = _claimed(session)
        first_checkpoint = _checkpoint(first.id)
        pause_claimed_job_for_human(session, first, first_checkpoint, now=NOW)
        cancel_human_checkpoint(
            session,
            checkpoint_id=first_checkpoint.id,
            actor_reference="user:operator",
            reason="operator cancelled checkpoint",
            now=NOW + timedelta(seconds=1),
        )
        first_job = session.get(CollectionJobRecord, first.id)
        assert first_job is not None
        assert first_job.status == JobStatus.CANCELLED.value

        assert schedule_due_jobs(session, [_schedule()], now=NOW + timedelta(minutes=15)) == 1
        second = claim_next_job(
            session,
            worker_id="worker-l17",
            now=NOW + timedelta(minutes=15),
        )
        assert second is not None
        second_checkpoint = HumanCheckpointRequest.from_correlation_token(
            binding=_binding(second.id),
            kind=HumanCheckpointKind.IDENTITY_VERIFICATION,
            correlation_token=TOKEN,
            session_reference="file-secret:///run/secrets/session.json",
            created_at=NOW + timedelta(minutes=15),
            expires_at=NOW + timedelta(minutes=30),
        )
        pause_claimed_job_for_human(
            session,
            second,
            second_checkpoint,
            now=NOW + timedelta(minutes=15),
        )
        assert invalidate_human_checkpoints_for_identity(
            session,
            delegated_identity_id=IDENTITY_ID,
            reason="delegated identity revoked",
            now=NOW + timedelta(minutes=16),
        ) == 1
        second_job = session.get(CollectionJobRecord, second.id)
        assert second_job is not None
        assert second_job.status == JobStatus.CANCELLED.value

        event_count = session.scalar(select(func.count(CollectionHumanCheckpointEventRecord.id)))
        assert event_count == 4


def test_second_waiting_checkpoint_for_same_job_is_rejected() -> None:
    factory = _factory()
    with factory.begin() as session:
        claimed = _claimed(session)
        pause_claimed_job_for_human(session, claimed, _checkpoint(claimed.id), now=NOW)
        job = session.get(CollectionJobRecord, claimed.id)
        assert job is not None
        job.status = JobStatus.RUNNING.value
        job.lease_owner = claimed.lease_owner
        job.lease_expires_at = NOW + timedelta(minutes=1)

        with pytest.raises(HumanCheckpointConflictError, match="already has"):
            pause_claimed_job_for_human(
                session,
                claimed,
                _checkpoint(claimed.id),
                now=NOW,
            )

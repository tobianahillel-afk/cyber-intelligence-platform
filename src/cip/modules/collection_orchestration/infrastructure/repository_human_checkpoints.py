from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.collection_orchestration.application.ports import ClaimedJob
from cip.modules.collection_orchestration.domain.human_checkpoints import (
    HumanCheckpointEventType,
    HumanCheckpointRequest,
    HumanCheckpointResumeRequest,
    HumanCheckpointState,
    correlation_matches,
    validate_actor_reference,
)
from cip.modules.collection_orchestration.domain.models import JobStatus
from cip.modules.collection_orchestration.infrastructure.models import (
    CollectionHumanCheckpointEventRecord,
    CollectionHumanCheckpointRecord,
    CollectionJobRecord,
)
from cip.modules.collection_orchestration.infrastructure.repository_common import (
    database_utc,
    owned_running_job,
)
from cip.shared.kernel.time import require_aware_utc


class HumanCheckpointError(RuntimeError):
    """Base error for durable human-checkpoint lifecycle failures."""


class HumanCheckpointConflictError(HumanCheckpointError):
    """A checkpoint transition conflicts with current durable job state."""


class HumanCheckpointResumeDeniedError(HumanCheckpointError):
    """A resume request does not match the durable checkpoint authority."""


def pause_claimed_job_for_human(
    session: Session,
    claimed: ClaimedJob,
    checkpoint: HumanCheckpointRequest,
    *,
    now: datetime,
) -> UUID:
    current = require_aware_utc(now, field_name="now")
    _validate_pause_binding(claimed, checkpoint)
    if checkpoint.created_at > current or checkpoint.expires_at <= current:
        raise ValueError("human checkpoint must be current when persisted")
    job = owned_running_job(session, claimed=claimed, now=current)
    existing = session.scalar(
        select(CollectionHumanCheckpointRecord)
        .where(
            CollectionHumanCheckpointRecord.job_id == claimed.id,
            CollectionHumanCheckpointRecord.state == HumanCheckpointState.WAITING.value,
        )
        .with_for_update()
    )
    if existing is not None:
        raise HumanCheckpointConflictError("job already has a waiting human checkpoint")
    session.add(_new_checkpoint_record(checkpoint))
    _append_event(
        session,
        checkpoint_id=checkpoint.id,
        job_id=claimed.id,
        event_type=HumanCheckpointEventType.CREATED,
        occurred_at=current,
        actor_reference=claimed.lease_owner,
        reason=checkpoint.kind.value,
    )
    job.status = JobStatus.AWAITING_HUMAN_CHECKPOINT.value
    job.lease_owner = None
    job.lease_expires_at = None
    job.finished_at = None
    job.human_resume_pending = False
    job.error_code = None
    job.error_message = None
    return checkpoint.id


def resume_human_checkpoint(
    session: Session,
    request: HumanCheckpointResumeRequest,
) -> UUID:
    current = request.resumed_at
    checkpoint = _waiting_checkpoint(session, request.checkpoint_id)
    _validate_resume_binding(checkpoint, request)
    if database_utc(checkpoint.expires_at) <= current:
        raise HumanCheckpointResumeDeniedError("human checkpoint has expired")
    if not correlation_matches(request.correlation_token, checkpoint.correlation_digest):
        raise HumanCheckpointResumeDeniedError("human checkpoint correlation mismatch")
    job = _waiting_job(session, checkpoint)
    checkpoint.state = HumanCheckpointState.COMPLETED.value
    checkpoint.completed_at = current
    _append_event(
        session,
        checkpoint_id=checkpoint.id,
        job_id=checkpoint.job_id,
        event_type=HumanCheckpointEventType.COMPLETED,
        occurred_at=current,
        actor_reference=request.actor_reference,
        reason=None,
    )
    job.status = JobStatus.PENDING.value
    job.available_at = current
    job.lease_owner = None
    job.lease_expires_at = None
    job.finished_at = None
    job.human_resume_pending = True
    job.error_code = None
    job.error_message = None
    return job.id


def cancel_human_checkpoint(
    session: Session,
    *,
    checkpoint_id: UUID,
    actor_reference: str,
    reason: str,
    now: datetime,
) -> UUID:
    current = require_aware_utc(now, field_name="now")
    actor = validate_actor_reference(actor_reference)
    normalized_reason = _safe_reason(reason)
    checkpoint = _waiting_checkpoint(session, checkpoint_id)
    checkpoint.state = HumanCheckpointState.CANCELLED.value
    checkpoint.cancelled_at = current
    _append_event(
        session,
        checkpoint_id=checkpoint.id,
        job_id=checkpoint.job_id,
        event_type=HumanCheckpointEventType.CANCELLED,
        occurred_at=current,
        actor_reference=actor,
        reason=normalized_reason,
    )
    _cancel_waiting_job(
        session,
        checkpoint,
        now=current,
        code="human_checkpoint_cancelled",
        message="human checkpoint cancelled",
    )
    return checkpoint.job_id


def expire_human_checkpoints(session: Session, *, now: datetime) -> int:
    current = require_aware_utc(now, field_name="now")
    records = session.scalars(
        select(CollectionHumanCheckpointRecord)
        .where(
            CollectionHumanCheckpointRecord.state == HumanCheckpointState.WAITING.value,
            CollectionHumanCheckpointRecord.expires_at <= current,
        )
        .with_for_update()
    ).all()
    for checkpoint in records:
        checkpoint.state = HumanCheckpointState.EXPIRED.value
        _append_event(
            session,
            checkpoint_id=checkpoint.id,
            job_id=checkpoint.job_id,
            event_type=HumanCheckpointEventType.EXPIRED,
            occurred_at=current,
            actor_reference="system:checkpoint-expiry",
            reason="checkpoint expired",
        )
        _cancel_waiting_job(
            session,
            checkpoint,
            now=current,
            code="human_checkpoint_expired",
            message="human checkpoint expired",
        )
    return len(records)


def invalidate_human_checkpoints_for_identity(
    session: Session,
    *,
    delegated_identity_id: UUID,
    reason: str,
    now: datetime,
) -> int:
    current = require_aware_utc(now, field_name="now")
    normalized_reason = _safe_reason(reason)
    records = session.scalars(
        select(CollectionHumanCheckpointRecord)
        .where(
            CollectionHumanCheckpointRecord.delegated_identity_id == delegated_identity_id,
            CollectionHumanCheckpointRecord.state == HumanCheckpointState.WAITING.value,
        )
        .with_for_update()
    ).all()
    for checkpoint in records:
        checkpoint.state = HumanCheckpointState.INVALIDATED.value
        checkpoint.invalidated_at = current
        _append_event(
            session,
            checkpoint_id=checkpoint.id,
            job_id=checkpoint.job_id,
            event_type=HumanCheckpointEventType.INVALIDATED,
            occurred_at=current,
            actor_reference="system:identity-invalidation",
            reason=normalized_reason,
        )
        _cancel_waiting_job(
            session,
            checkpoint,
            now=current,
            code="human_checkpoint_invalidated",
            message="human checkpoint invalidated",
        )
    return len(records)


def _new_checkpoint_record(checkpoint: HumanCheckpointRequest) -> CollectionHumanCheckpointRecord:
    binding = checkpoint.binding
    return CollectionHumanCheckpointRecord(
        id=checkpoint.id,
        job_id=binding.job_id,
        source_id=binding.source_id,
        adapter_id=binding.adapter_id,
        delegated_identity_id=binding.delegated_identity_id,
        purpose=binding.purpose,
        kind=checkpoint.kind.value,
        state=HumanCheckpointState.WAITING.value,
        correlation_digest=checkpoint.correlation_digest,
        session_reference=checkpoint.session_reference,
        created_at=checkpoint.created_at,
        expires_at=checkpoint.expires_at,
    )


def _waiting_checkpoint(session: Session, checkpoint_id: UUID) -> CollectionHumanCheckpointRecord:
    checkpoint = session.get(
        CollectionHumanCheckpointRecord,
        checkpoint_id,
        with_for_update=True,
    )
    if checkpoint is None:
        raise HumanCheckpointResumeDeniedError("human checkpoint was not found")
    if checkpoint.state != HumanCheckpointState.WAITING.value:
        raise HumanCheckpointResumeDeniedError("human checkpoint is not waiting")
    return checkpoint


def _waiting_job(
    session: Session,
    checkpoint: CollectionHumanCheckpointRecord,
) -> CollectionJobRecord:
    job = session.get(CollectionJobRecord, checkpoint.job_id, with_for_update=True)
    if job is None or job.status != JobStatus.AWAITING_HUMAN_CHECKPOINT.value:
        raise HumanCheckpointConflictError("job is not awaiting a human checkpoint")
    if job.source_id != checkpoint.source_id or job.adapter_id != checkpoint.adapter_id:
        raise HumanCheckpointConflictError("human checkpoint job binding changed")
    return job


def _cancel_waiting_job(
    session: Session,
    checkpoint: CollectionHumanCheckpointRecord,
    *,
    now: datetime,
    code: str,
    message: str,
) -> None:
    job = session.get(CollectionJobRecord, checkpoint.job_id, with_for_update=True)
    if job is None or job.status != JobStatus.AWAITING_HUMAN_CHECKPOINT.value:
        return
    job.status = JobStatus.CANCELLED.value
    job.finished_at = now
    job.lease_owner = None
    job.lease_expires_at = None
    job.human_resume_pending = False
    job.error_code = code
    job.error_message = message


def _validate_pause_binding(claimed: ClaimedJob, checkpoint: HumanCheckpointRequest) -> None:
    binding = checkpoint.binding
    if (
        binding.job_id != claimed.id
        or binding.source_id != claimed.source_id
        or binding.adapter_id != claimed.adapter_id
    ):
        raise HumanCheckpointConflictError("human checkpoint does not match claimed job")


def _validate_resume_binding(
    checkpoint: CollectionHumanCheckpointRecord,
    request: HumanCheckpointResumeRequest,
) -> None:
    binding = request.binding
    if (
        checkpoint.job_id != binding.job_id
        or checkpoint.source_id != binding.source_id
        or checkpoint.adapter_id != binding.adapter_id
        or checkpoint.delegated_identity_id != binding.delegated_identity_id
        or checkpoint.purpose != binding.purpose
    ):
        raise HumanCheckpointResumeDeniedError("human checkpoint binding mismatch")


def _append_event(
    session: Session,
    *,
    checkpoint_id: UUID,
    job_id: UUID,
    event_type: HumanCheckpointEventType,
    occurred_at: datetime,
    actor_reference: str,
    reason: str | None,
) -> None:
    session.add(
        CollectionHumanCheckpointEventRecord(
            id=uuid4(),
            checkpoint_id=checkpoint_id,
            job_id=job_id,
            event_type=event_type.value,
            occurred_at=occurred_at,
            actor_reference=validate_actor_reference(actor_reference),
            reason=reason,
        )
    )


def _safe_reason(value: str) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > 500:
        raise ValueError("reason must be 1..500 characters")
    return normalized

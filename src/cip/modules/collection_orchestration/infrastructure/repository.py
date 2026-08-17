"""Stable public repository facade for durable collection orchestration."""

from cip.modules.collection_orchestration.infrastructure.repository_common import (
    LeaseLostError,
)
from cip.modules.collection_orchestration.infrastructure.repository_completion import (
    cancel_claimed_job,
    complete_job,
    persist_partial_progress,
)
from cip.modules.collection_orchestration.infrastructure.repository_failures import (
    fail_job,
    recover_expired_leases,
)
from cip.modules.collection_orchestration.infrastructure.repository_human_checkpoints import (
    HumanCheckpointConflictError,
    HumanCheckpointError,
    HumanCheckpointResumeDeniedError,
    cancel_human_checkpoint,
    expire_human_checkpoints,
    invalidate_human_checkpoints_for_identity,
    pause_claimed_job_for_human,
    resume_human_checkpoint,
)
from cip.modules.collection_orchestration.infrastructure.repository_queue import (
    claim_next_job,
    enqueue_job,
    has_active_job,
    heartbeat_job,
)

__all__ = [
    "HumanCheckpointConflictError",
    "HumanCheckpointError",
    "HumanCheckpointResumeDeniedError",
    "LeaseLostError",
    "cancel_claimed_job",
    "cancel_human_checkpoint",
    "claim_next_job",
    "complete_job",
    "enqueue_job",
    "expire_human_checkpoints",
    "fail_job",
    "has_active_job",
    "heartbeat_job",
    "invalidate_human_checkpoints_for_identity",
    "pause_claimed_job_for_human",
    "persist_partial_progress",
    "recover_expired_leases",
    "resume_human_checkpoint",
]

"""Stable collection-orchestration persistence facade.

The implementation lives in focused repository modules so this public import surface remains
stable without allowing one persistence file to grow into an architecture bottleneck.
"""

from __future__ import annotations

from cip.modules.collection_orchestration.infrastructure.repository_backfill import (
    backfill_batch,
    backfill_finish,
)
from cip.modules.collection_orchestration.infrastructure.repository_circuits import (
    circuit_allows_claim,
    record_failure,
    reset_circuit,
)
from cip.modules.collection_orchestration.infrastructure.repository_common import LeaseLostError
from cip.modules.collection_orchestration.infrastructure.repository_completion import (
    advance_checkpoint,
    advance_partial_checkpoint,
    cancel_claimed_job,
    complete_job,
    insert_observations,
    observation_values,
    persist_partial_progress,
)
from cip.modules.collection_orchestration.infrastructure.repository_failures import fail_job
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
    cancel_queued_job,
    claim_next_job,
    enqueue_job,
    has_active_job,
    heartbeat_job,
    recover_expired_leases,
)

__all__ = [
    "HumanCheckpointConflictError",
    "HumanCheckpointError",
    "HumanCheckpointResumeDeniedError",
    "LeaseLostError",
    "advance_checkpoint",
    "advance_partial_checkpoint",
    "backfill_batch",
    "backfill_finish",
    "cancel_claimed_job",
    "cancel_human_checkpoint",
    "cancel_queued_job",
    "circuit_allows_claim",
    "claim_next_job",
    "complete_job",
    "enqueue_job",
    "expire_human_checkpoints",
    "fail_job",
    "has_active_job",
    "heartbeat_job",
    "insert_observations",
    "invalidate_human_checkpoints_for_identity",
    "observation_values",
    "pause_claimed_job_for_human",
    "persist_partial_progress",
    "record_failure",
    "recover_expired_leases",
    "reset_circuit",
    "resume_human_checkpoint",
]

"""Stable public repository facade for durable collection orchestration."""

from cip.modules.collection_orchestration.infrastructure.repository_common import (
    LeaseLostError,
)
from cip.modules.collection_orchestration.infrastructure.repository_completion import (
    complete_job,
)
from cip.modules.collection_orchestration.infrastructure.repository_failures import (
    fail_job,
    recover_expired_leases,
)
from cip.modules.collection_orchestration.infrastructure.repository_queue import (
    claim_next_job,
    enqueue_job,
    has_active_job,
    heartbeat_job,
)

__all__ = [
    "LeaseLostError",
    "claim_next_job",
    "complete_job",
    "enqueue_job",
    "fail_job",
    "has_active_job",
    "heartbeat_job",
    "recover_expired_leases",
]

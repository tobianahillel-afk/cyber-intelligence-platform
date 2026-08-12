from __future__ import annotations

from datetime import datetime

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    SourceRuntimeState,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


class PublicWebCollectionDeniedError(RuntimeError):
    """Source or target governance denied public-web collection."""


def authorize_public_web_url(
    entry: SourceRegistryEntry,
    target_url: str,
    *,
    now: datetime,
) -> None:
    decision = entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.OFFICIAL_DOCUMENT_DISCOVERY,
            target_url=target_url,
            purpose="corporate-public-footprint",
            automated=True,
            store_raw_content=False,
            human_review_completed=False,
        ),
        entry.authorization,
        SourceRuntimeState(remaining_requests=1),
        now=now,
    )
    if not decision.allowed:
        raise PublicWebCollectionDeniedError(decision.reason.value)


def checked_total_bytes(target: PublicWebTarget, value: int) -> int:
    if value > target.max_total_bytes:
        raise PublicWebCollectionDeniedError("total_byte_budget_exceeded")
    return value

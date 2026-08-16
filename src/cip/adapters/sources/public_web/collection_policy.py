from __future__ import annotations

from datetime import datetime

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.source_governance.domain.models import (
    CollectionDecision,
    CollectionRequest,
    DataCategory,
    HttpMethod,
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
    http_method: HttpMethod = HttpMethod.GET,
    purpose: str = "corporate-public-footprint",
    store_raw_content: bool = False,
) -> None:
    decision = _evaluate_public_web_request(
        entry,
        target_url,
        now=now,
        http_method=http_method,
        purpose=purpose,
        store_raw_content=store_raw_content,
    )
    if not decision.allowed:
        raise PublicWebCollectionDeniedError(decision.reason.value)


def public_web_raw_storage_allowed(
    entry: SourceRegistryEntry,
    target_url: str,
    *,
    now: datetime,
    purpose: str = "corporate-public-footprint",
) -> bool:
    return _evaluate_public_web_request(
        entry,
        target_url,
        now=now,
        http_method=HttpMethod.GET,
        purpose=purpose,
        store_raw_content=True,
    ).allowed


def _evaluate_public_web_request(
    entry: SourceRegistryEntry,
    target_url: str,
    *,
    now: datetime,
    http_method: HttpMethod,
    purpose: str,
    store_raw_content: bool,
) -> CollectionDecision:
    return entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.OFFICIAL_DOCUMENT_DISCOVERY,
            target_url=target_url,
            purpose=purpose,
            http_method=http_method,
            automated=True,
            store_raw_content=store_raw_content,
            human_review_completed=False,
        ),
        entry.authorization,
        SourceRuntimeState(remaining_requests=1),
        now=now,
    )


def checked_total_bytes(target: PublicWebTarget, value: int) -> int:
    if value > target.max_total_bytes:
        raise PublicWebCollectionDeniedError("total_byte_budget_exceeded")
    return value

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import ValidationError

from cip.adapters.sources.ted_search.client import (
    TedSearchCheckpoint,
    TedSearchClient,
)
from cip.adapters.sources.ted_search.mapper import map_ted_notice
from cip.adapters.sources.ted_search.schemas import TedSearchResponse
from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.organizations.domain.entities import Organization
from cip.modules.procurement_history.domain.models import ProcurementHistoryProjection
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    SourceRuntimeState,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc


class TedCollectionDeniedError(RuntimeError):
    """Source governance denied TED collection."""


class TedSourceSchemaError(RuntimeError):
    """TED payload no longer matches the approved selected-field schema."""


@dataclass(frozen=True, slots=True)
class TedCollectionBatch:
    observations: tuple[RawObservation, ...]
    projections: tuple[CommercialProjection, ...]
    buyers: tuple[Organization, ...]
    procurement: tuple[ProcurementHistoryProjection, ...]
    checkpoint: TedSearchCheckpoint
    not_modified: bool


def collect_ted_notices(
    client: TedSearchClient,
    entry: SourceRegistryEntry,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: TedSearchCheckpoint | None = None,
) -> TedCollectionBatch:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    decision = entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.PUBLIC_TENDER,
            target_url=entry.policy.base_url,
            purpose="procurement-intelligence",
            automated=True,
            store_raw_content=False,
            human_review_completed=False,
        ),
        entry.authorization,
        SourceRuntimeState(remaining_requests=1),
        now=collected,
    )
    if not decision.allowed:
        raise TedCollectionDeniedError(decision.reason.value)
    try:
        response = TedSearchResponse.model_validate_json(client.fetch().body)
    except ValidationError as exc:
        raise TedSourceSchemaError("TED search schema validation failed") from exc

    latest = response.notices[0].publication_number if response.notices else None
    observations: list[RawObservation] = []
    projections: list[CommercialProjection] = []
    buyers: dict[UUID, Organization] = {}
    procurement: list[ProcurementHistoryProjection] = []
    previous = checkpoint.latest_publication_number if checkpoint else None
    for notice in response.notices:
        if previous is not None and notice.publication_number == previous:
            break
        mapped = map_ted_notice(
            notice,
            collection_job_id=collection_job_id,
            collected_at=collected,
            retention_until=retention_until,
        )
        if mapped is None:
            continue
        observations.append(mapped.observation)
        buyers[mapped.buyer.id] = mapped.buyer
        procurement.append(mapped.procurement)
        if mapped.projection is not None:
            projections.append(mapped.projection)
    next_checkpoint = TedSearchCheckpoint(
        latest_publication_number=latest or previous,
    )
    not_modified = bool(previous is not None and latest == previous)
    return TedCollectionBatch(
        observations=tuple(observations),
        projections=tuple(projections),
        buyers=tuple(buyers.values()),
        procurement=tuple(procurement),
        checkpoint=next_checkpoint,
        not_modified=not_modified,
    )

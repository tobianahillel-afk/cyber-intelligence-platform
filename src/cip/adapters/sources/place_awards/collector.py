from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import ValidationError

from cip.adapters.sources.place_awards.client import PlaceAwardsClient
from cip.adapters.sources.place_awards.mapper import map_place_award
from cip.adapters.sources.place_awards.schemas import PlaceAwardsResponse
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


class PlaceCollectionDeniedError(RuntimeError):
    """Source governance denied PLACE award collection."""


class PlaceSourceSchemaError(RuntimeError):
    """PLACE payload no longer matches the selected-field schema."""


class PlaceSourceWindowError(RuntimeError):
    """The PLACE checkpoint was not reached inside the bounded page window."""


@dataclass(frozen=True, slots=True)
class PlaceCheckpoint:
    latest_source_record_key: str | None = None
    latest_notification_date: str | None = None


@dataclass(frozen=True, slots=True)
class PlaceCollectionBatch:
    observations: tuple[RawObservation, ...]
    buyers: tuple[Organization, ...]
    procurement: tuple[ProcurementHistoryProjection, ...]
    checkpoint: PlaceCheckpoint
    not_modified: bool


def collect_place_awards(
    client: PlaceAwardsClient,
    entry: SourceRegistryEntry,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: PlaceCheckpoint | None = None,
    max_pages: int = 5,
) -> PlaceCollectionBatch:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    _authorize(entry, collected_at=collected)
    if max_pages < 1:
        raise ValueError("max_pages must be positive")
    previous = checkpoint.latest_source_record_key if checkpoint else None
    observations: list[RawObservation] = []
    buyers: dict[UUID, Organization] = {}
    procurement: list[ProcurementHistoryProjection] = []
    newest_key: str | None = None
    newest_date: str | None = None
    checkpoint_reached = False
    last_page_size = 0
    total_count = 0

    for page_index in range(max_pages):
        response = _parse_response(
            client.fetch_page(offset=page_index * client.PAGE_SIZE).body
        )
        total_count = response.total_count
        last_page_size = len(response.results)
        for award in response.results:
            mapped = map_place_award(
                award,
                collection_job_id=collection_job_id,
                collected_at=collected,
                retention_until=retention_until,
            )
            record_key = mapped.observation.source_record_key
            if newest_key is None:
                newest_key = record_key
                newest_date = award.date_de_notification.isoformat()
            if previous is not None and record_key == previous:
                checkpoint_reached = True
                break
            observations.append(mapped.observation)
            buyers[mapped.buyer.id] = mapped.buyer
            procurement.append(mapped.procurement)
        if checkpoint_reached or last_page_size < client.PAGE_SIZE:
            break

    if (
        previous is not None
        and not checkpoint_reached
        and last_page_size == client.PAGE_SIZE
        and total_count > max_pages * client.PAGE_SIZE
    ):
        raise PlaceSourceWindowError(
            "PLACE checkpoint was not reached within the configured page budget"
        )

    next_checkpoint = PlaceCheckpoint(
        latest_source_record_key=newest_key or previous,
        latest_notification_date=(
            newest_date or (checkpoint.latest_notification_date if checkpoint else None)
        ),
    )
    return PlaceCollectionBatch(
        observations=tuple(observations),
        buyers=tuple(buyers.values()),
        procurement=tuple(procurement),
        checkpoint=next_checkpoint,
        not_modified=bool(previous is not None and newest_key == previous),
    )


def _authorize(entry: SourceRegistryEntry, *, collected_at: datetime) -> None:
    decision = entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.CONTRACT_AWARD,
            target_url=entry.policy.base_url,
            purpose="procurement-history-intelligence",
            automated=True,
            store_raw_content=False,
            human_review_completed=False,
        ),
        entry.authorization,
        SourceRuntimeState(remaining_requests=1),
        now=collected_at,
    )
    if not decision.allowed:
        raise PlaceCollectionDeniedError(decision.reason.value)


def _parse_response(body: bytes) -> PlaceAwardsResponse:
    try:
        return PlaceAwardsResponse.model_validate_json(body)
    except ValidationError as exc:
        raise PlaceSourceSchemaError("PLACE response schema validation failed") from exc

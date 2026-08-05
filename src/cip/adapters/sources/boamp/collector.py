from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID

from pydantic import ValidationError

from cip.adapters.sources.boamp.client import BoampCheckpoint, BoampClient
from cip.adapters.sources.boamp.mapper import map_boamp_notice
from cip.adapters.sources.boamp.schemas import BoampResponse
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


class BoampCollectionDeniedError(RuntimeError):
    """Source governance denied BOAMP collection."""


class BoampSourceSchemaError(RuntimeError):
    """BOAMP payload no longer matches the selected-field schema."""


class BoampSourceWindowError(RuntimeError):
    """The bounded BOAMP pagination window could not be consumed safely."""


@dataclass(frozen=True, slots=True)
class BoampCollectionBatch:
    observations: tuple[RawObservation, ...]
    projections: tuple[CommercialProjection, ...]
    buyers: tuple[Organization, ...]
    procurement: tuple[ProcurementHistoryProjection, ...]
    checkpoint: BoampCheckpoint
    not_modified: bool


def collect_boamp_notices(
    client: BoampClient,
    entry: SourceRegistryEntry,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: BoampCheckpoint | None = None,
    max_pages: int = 5,
) -> BoampCollectionBatch:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    _authorize(entry, collected_at=collected)
    if max_pages < 1:
        raise ValueError("max_pages must be positive")
    previous_id = checkpoint.latest_idweb if checkpoint else None
    since_date = _since_date(checkpoint, collected_at=collected)
    observations: list[RawObservation] = []
    projections: list[CommercialProjection] = []
    buyers: dict[UUID, Organization] = {}
    procurement: list[ProcurementHistoryProjection] = []
    newest_id: str | None = None
    newest_date: str | None = None
    checkpoint_reached = False

    for page_index in range(max_pages):
        response = _parse_response(
            client.fetch_page(
                since_date=since_date,
                offset=page_index * client.PAGE_SIZE,
            ).body
        )
        if page_index == 0 and response.results:
            newest_id = response.results[0].idweb
            newest_date = _publication_date(response.results[0].publication_timestamp())
        for notice in response.results:
            if previous_id is not None and notice.idweb == previous_id:
                checkpoint_reached = True
                break
            mapped = map_boamp_notice(
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
        if checkpoint_reached or len(response.results) < client.PAGE_SIZE:
            break
        if page_index == max_pages - 1:
            consumed = max_pages * client.PAGE_SIZE
            if response.total_count > consumed:
                raise BoampSourceWindowError(
                    "BOAMP result window exceeded the configured pagination budget"
                )

    next_checkpoint = BoampCheckpoint(
        latest_idweb=newest_id or previous_id,
        latest_publication_date=newest_date
        or (checkpoint.latest_publication_date if checkpoint else None),
    )
    return BoampCollectionBatch(
        observations=tuple(observations),
        projections=tuple(projections),
        buyers=tuple(buyers.values()),
        procurement=tuple(procurement),
        checkpoint=next_checkpoint,
        not_modified=bool(previous_id is not None and newest_id == previous_id),
    )


def _authorize(entry: SourceRegistryEntry, *, collected_at: datetime) -> None:
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
        now=collected_at,
    )
    if not decision.allowed:
        raise BoampCollectionDeniedError(decision.reason.value)


def _parse_response(body: bytes) -> BoampResponse:
    try:
        return BoampResponse.model_validate_json(body)
    except ValidationError as exc:
        raise BoampSourceSchemaError("BOAMP response schema validation failed") from exc


def _since_date(checkpoint: BoampCheckpoint | None, *, collected_at: datetime) -> date:
    if checkpoint and checkpoint.latest_publication_date:
        try:
            return date.fromisoformat(checkpoint.latest_publication_date)
        except ValueError as exc:
            raise BoampSourceSchemaError("invalid checkpoint publication date") from exc
    return (collected_at - timedelta(days=2)).date()


def _publication_date(value: datetime | None) -> str | None:
    return value.date().isoformat() if value is not None else None

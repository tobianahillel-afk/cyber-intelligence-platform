from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import ValidationError

from cip.adapters.sources.decp.client import DecpCheckpoint, DecpClient
from cip.adapters.sources.decp.mapper import map_decp_contract
from cip.adapters.sources.decp.schemas import DecpResponse
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


class DecpCollectionDeniedError(RuntimeError):
    """Source governance denied DECP collection."""


class DecpSourceSchemaError(RuntimeError):
    """DECP payload no longer matches the selected-field schema."""


class DecpSourceWindowError(RuntimeError):
    """The DECP checkpoint was not reached within the bounded window."""


@dataclass(frozen=True, slots=True)
class DecpCollectionBatch:
    observations: tuple[RawObservation, ...]
    buyers: tuple[Organization, ...]
    procurement: tuple[ProcurementHistoryProjection, ...]
    checkpoint: DecpCheckpoint
    not_modified: bool


def collect_decp_contracts(
    client: DecpClient,
    entry: SourceRegistryEntry,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: DecpCheckpoint | None = None,
    max_pages: int = 5,
) -> DecpCollectionBatch:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    _authorize(entry, collected_at=collected)
    if max_pages < 1:
        raise ValueError("max_pages must be positive")
    previous = checkpoint.latest_revision_key if checkpoint else None
    observations: list[RawObservation] = []
    buyers: dict[UUID, Organization] = {}
    procurement: list[ProcurementHistoryProjection] = []
    newest_revision: str | None = None
    newest_publication_date: str | None = None
    checkpoint_reached = False

    for page_index in range(max_pages):
        response = _parse_response(
            client.fetch_page(offset=page_index * client.PAGE_SIZE).body
        )
        for contract in response.results:
            mapped = map_decp_contract(
                contract,
                collection_job_id=collection_job_id,
                collected_at=collected,
                retention_until=retention_until,
            )
            if mapped is None:
                continue
            revision_key = mapped.procurement.publication.revision_key
            if newest_revision is None:
                newest_revision = revision_key
                published = mapped.procurement.publication.published_at
                newest_publication_date = published.date().isoformat() if published else None
            if previous is not None and revision_key == previous:
                checkpoint_reached = True
                break
            observations.append(mapped.observation)
            buyers[mapped.buyer.id] = mapped.buyer
            procurement.append(mapped.procurement)
        if checkpoint_reached or len(response.results) < client.PAGE_SIZE:
            break
    if previous is not None and not checkpoint_reached and max_pages * client.PAGE_SIZE > 0:
        last_page_full = response.total_count > max_pages * client.PAGE_SIZE
        if last_page_full:
            raise DecpSourceWindowError(
                "DECP checkpoint was not reached within the configured page budget"
            )

    next_checkpoint = DecpCheckpoint(
        latest_revision_key=newest_revision or previous,
        latest_publication_date=(
            newest_publication_date
            or (checkpoint.latest_publication_date if checkpoint else None)
        ),
    )
    return DecpCollectionBatch(
        observations=tuple(observations),
        buyers=tuple(buyers.values()),
        procurement=tuple(procurement),
        checkpoint=next_checkpoint,
        not_modified=bool(previous is not None and newest_revision == previous),
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
        raise DecpCollectionDeniedError(decision.reason.value)


def _parse_response(body: bytes) -> DecpResponse:
    try:
        return DecpResponse.model_validate_json(body)
    except ValidationError as exc:
        raise DecpSourceSchemaError("DECP response schema validation failed") from exc

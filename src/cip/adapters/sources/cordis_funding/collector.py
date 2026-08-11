from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import unquote, urlsplit
from uuid import UUID

from pydantic import ValidationError

from cip.adapters.sources.cordis_funding.client import CordisFundingClient
from cip.adapters.sources.cordis_funding.mapper import map_cordis_funding_binding
from cip.adapters.sources.cordis_funding.schemas import CordisFundingResponse
from cip.modules.corporate_changes.domain.models import ChangeClaimSnapshot
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    SourceRuntimeState,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc


class CordisFundingCollectionDeniedError(RuntimeError):
    """Source governance denied CORDIS collection."""


class CordisFundingSchemaError(RuntimeError):
    """CORDIS SPARQL payload no longer matches the selected schema."""


class CordisFundingPaginationError(RuntimeError):
    """CORDIS pagination state is unsafe."""


@dataclass(frozen=True, slots=True)
class CordisFundingCheckpoint:
    offset: int = 0


@dataclass(frozen=True, slots=True)
class CordisFundingCollectionBatch:
    observations: tuple[RawObservation, ...]
    claims: tuple[ChangeClaimSnapshot, ...]
    checkpoint: CordisFundingCheckpoint | None
    not_modified: bool


def collect_cordis_funding(
    client: CordisFundingClient,
    entry: SourceRegistryEntry,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: CordisFundingCheckpoint | None = None,
    max_pages: int = 5,
) -> CordisFundingCollectionBatch:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    if max_pages < 1:
        raise ValueError("max_pages must be positive")
    offset = checkpoint.offset if checkpoint else 0
    if offset < 0:
        raise CordisFundingPaginationError("CORDIS offset cannot be negative")
    observations: list[RawObservation] = []
    claims: list[ChangeClaimSnapshot] = []
    next_checkpoint: CordisFundingCheckpoint | None = None

    for _page_index in range(max_pages):
        target_url = client.page_url(offset)
        _validate_page_url(entry, target_url)
        _authorize(entry, target_url, collected_at=collected)
        response = _parse_response(client.fetch_url(target_url).body)
        bindings = response.results.bindings
        for binding in bindings:
            observation, claim = map_cordis_funding_binding(
                binding,
                collection_job_id=collection_job_id,
                collected_at=collected,
                retention_until=retention_until,
            )
            observations.append(observation)
            claims.append(claim)
        if len(bindings) < client.PAGE_SIZE:
            next_checkpoint = None
            break
        offset += client.PAGE_SIZE
        next_checkpoint = CordisFundingCheckpoint(offset=offset)

    return CordisFundingCollectionBatch(
        observations=tuple(observations),
        claims=tuple(claims),
        checkpoint=next_checkpoint,
        not_modified=not observations,
    )


def _validate_page_url(entry: SourceRegistryEntry, url: str) -> None:
    parsed = urlsplit(url)
    base = urlsplit(entry.policy.base_url)
    if parsed.scheme != "https" or parsed.hostname != base.hostname:
        raise CordisFundingPaginationError("CORDIS URL outside provider host")
    if unquote(parsed.path).rstrip("/") != unquote(base.path).rstrip("/"):
        raise CordisFundingPaginationError("CORDIS URL outside SPARQL endpoint")


def _authorize(
    entry: SourceRegistryEntry,
    target_url: str,
    *,
    collected_at: datetime,
) -> None:
    decision = entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.PUBLIC_RESULT_METADATA,
            target_url=target_url,
            purpose="public-funding-intelligence",
            automated=True,
            store_raw_content=False,
            human_review_completed=False,
        ),
        entry.authorization,
        SourceRuntimeState(remaining_requests=1),
        now=collected_at,
    )
    if not decision.allowed:
        raise CordisFundingCollectionDeniedError(decision.reason.value)


def _parse_response(body: bytes) -> CordisFundingResponse:
    try:
        return CordisFundingResponse.model_validate_json(body)
    except ValidationError as exc:
        raise CordisFundingSchemaError(
            "CORDIS funding response schema validation failed"
        ) from exc

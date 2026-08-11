from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import unquote, urljoin, urlsplit
from uuid import UUID

from pydantic import ValidationError

from cip.adapters.sources.ademe_funding.client import AdemeFundingClient
from cip.adapters.sources.ademe_funding.mapper import map_ademe_funding_line
from cip.adapters.sources.ademe_funding.schemas import AdemeFundingResponse
from cip.modules.corporate_changes.domain.models import ChangeClaimSnapshot
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    SourceRuntimeState,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc


class AdemeFundingCollectionDeniedError(RuntimeError):
    """Source governance denied ADEME funding collection."""


class AdemeFundingSchemaError(RuntimeError):
    """ADEME funding payload no longer matches the selected-field schema."""


class AdemeFundingPaginationError(RuntimeError):
    """ADEME returned an unsafe pagination cursor."""


@dataclass(frozen=True, slots=True)
class AdemeFundingCheckpoint:
    next_url: str | None = None


@dataclass(frozen=True, slots=True)
class AdemeFundingCollectionBatch:
    observations: tuple[RawObservation, ...]
    claims: tuple[ChangeClaimSnapshot, ...]
    checkpoint: AdemeFundingCheckpoint
    not_modified: bool


def collect_ademe_funding(
    client: AdemeFundingClient,
    entry: SourceRegistryEntry,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: AdemeFundingCheckpoint | None = None,
    max_pages: int = 5,
) -> AdemeFundingCollectionBatch:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    if max_pages < 1:
        raise ValueError("max_pages must be positive")
    current_url = (
        checkpoint.next_url
        if checkpoint and checkpoint.next_url
        else client.first_page_url()
    )
    observations: list[RawObservation] = []
    claims: list[ChangeClaimSnapshot] = []
    visited: set[str] = set()
    next_url: str | None = current_url

    for _page_index in range(max_pages):
        if next_url is None:
            break
        normalized = _validate_page_url(entry, next_url)
        if normalized in visited:
            raise AdemeFundingPaginationError("ADEME pagination loop detected")
        visited.add(normalized)
        _authorize(entry, normalized, collected_at=collected)
        response = _parse_response(client.fetch_url(normalized).body)
        for line in response.results:
            observation, claim = map_ademe_funding_line(
                line,
                collection_job_id=collection_job_id,
                collected_at=collected,
                retention_until=retention_until,
            )
            observations.append(observation)
            claims.append(claim)
        next_url = _resolve_next(entry.policy.base_url, response.next)

    return AdemeFundingCollectionBatch(
        observations=tuple(observations),
        claims=tuple(claims),
        checkpoint=AdemeFundingCheckpoint(next_url=next_url),
        not_modified=not observations,
    )


def _validate_page_url(entry: SourceRegistryEntry, url: str) -> str:
    parsed = urlsplit(url)
    base = urlsplit(entry.policy.base_url)
    if parsed.scheme != "https" or parsed.hostname != base.hostname:
        raise AdemeFundingPaginationError("ADEME pagination URL outside provider host")
    path = unquote(parsed.path)
    expected = unquote(base.path).rstrip("/")
    if path.rstrip("/") != expected:
        raise AdemeFundingPaginationError("ADEME pagination URL outside lines endpoint")
    return url


def _resolve_next(base_url: str, value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return urljoin(base_url, normalized)


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
        raise AdemeFundingCollectionDeniedError(decision.reason.value)


def _parse_response(body: bytes) -> AdemeFundingResponse:
    try:
        return AdemeFundingResponse.model_validate_json(body)
    except ValidationError as exc:
        raise AdemeFundingSchemaError(
            "ADEME funding response schema validation failed"
        ) from exc

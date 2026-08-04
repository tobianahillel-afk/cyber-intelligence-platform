from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from uuid import UUID

from pydantic import ValidationError

from cip.adapters.sources.lever.client import LeverClient
from cip.adapters.sources.lever.mapper import (
    lever_posting_to_canonical,
    map_lever_posting,
)
from cip.adapters.sources.lever.registry import LeverSite
from cip.adapters.sources.lever.schemas import LeverPosting, LeverPostingsResponse
from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    SourceRuntimeState,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc


class LeverCollectionDeniedError(RuntimeError):
    """Source governance denied Lever collection."""


class LeverSourceSchemaError(RuntimeError):
    """Lever payload no longer matches the approved schema."""


class LeverSourceWindowError(RuntimeError):
    """A Lever site exceeds the configured safe job count."""


@dataclass(frozen=True, slots=True)
class LeverCheckpoint:
    fingerprints: Mapping[str, Mapping[str, str]]

    def __post_init__(self) -> None:
        copied = {
            site_id: MappingProxyType(dict(values))
            for site_id, values in self.fingerprints.items()
        }
        object.__setattr__(self, "fingerprints", MappingProxyType(copied))


@dataclass(frozen=True, slots=True)
class LeverCollectionBatch:
    observations: tuple[RawObservation, ...]
    projections: tuple[CommercialProjection, ...]
    checkpoint: LeverCheckpoint
    not_modified: bool


def collect_lever_jobs(
    client: LeverClient,
    entry: SourceRegistryEntry,
    sites: tuple[LeverSite, ...],
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: LeverCheckpoint | None = None,
    page_size: int = 100,
    max_jobs_per_site: int = 5_000,
) -> LeverCollectionBatch:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    enabled_sites = tuple(site for site in sites if site.enabled)
    if not enabled_sites:
        raise ValueError("at least one Lever site must be enabled")
    if not 1 <= page_size <= 100:
        raise ValueError("page_size must be between 1 and 100")
    if max_jobs_per_site < 1:
        raise ValueError("max_jobs_per_site must be positive")
    previous = checkpoint.fingerprints if checkpoint else {}
    current: dict[str, dict[str, str]] = {}
    observations: list[RawObservation] = []
    projections: list[CommercialProjection] = []

    for site in enabled_sites:
        _authorize(entry, client.postings_url(site.site_token), collected_at=collected)
        postings = _fetch_site(
            client,
            site,
            page_size=page_size,
            max_jobs=max_jobs_per_site,
        )
        current[site.id] = _collect_site(
            site,
            postings,
            previous=previous.get(site.id, {}),
            collection_job_id=collection_job_id,
            collected_at=collected,
            retention_until=retention_until,
            observations=observations,
            projections=projections,
        )

    current_checkpoint = LeverCheckpoint(current)
    return LeverCollectionBatch(
        observations=tuple(observations),
        projections=tuple(projections),
        checkpoint=current_checkpoint,
        not_modified=_checkpoint_equal(previous, current_checkpoint.fingerprints),
    )


def _fetch_site(
    client: LeverClient,
    site: LeverSite,
    *,
    page_size: int,
    max_jobs: int,
) -> tuple[LeverPosting, ...]:
    postings: list[LeverPosting] = []
    skip = 0
    while True:
        response = _parse_response(
            client.fetch_postings(
                site.site_token,
                skip=skip,
                limit=page_size,
            ).body
        )
        page = response.root
        postings.extend(page)
        if len(postings) > max_jobs:
            raise LeverSourceWindowError("Lever site exceeds configured job limit")
        if len(page) < page_size:
            return tuple(postings)
        skip += len(page)


def _collect_site(
    site: LeverSite,
    postings: tuple[LeverPosting, ...],
    *,
    previous: Mapping[str, str],
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    observations: list[RawObservation],
    projections: list[CommercialProjection],
) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for posting in postings:
        key = posting.id
        if key in fingerprints:
            raise LeverSourceSchemaError(f"duplicate posting id on site {site.id}: {key}")
        fingerprint = lever_posting_to_canonical(site, posting).fingerprint()
        fingerprints[key] = fingerprint
        mapped = map_lever_posting(
            site,
            posting,
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
        )
        if mapped is None:
            continue
        observation, projection = mapped
        projections.append(projection)
        if previous.get(key) != fingerprint:
            observations.append(observation)
    return fingerprints


def _authorize(entry: SourceRegistryEntry, target_url: str, *, collected_at: datetime) -> None:
    decision = entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.PUBLIC_JOB_POSTING,
            target_url=target_url,
            purpose="commercial-hiring-intelligence",
            automated=True,
            store_raw_content=False,
            human_review_completed=False,
        ),
        entry.authorization,
        SourceRuntimeState(remaining_requests=1),
        now=collected_at,
    )
    if not decision.allowed:
        raise LeverCollectionDeniedError(decision.reason.value)


def _parse_response(body: bytes) -> LeverPostingsResponse:
    try:
        return LeverPostingsResponse.model_validate_json(body)
    except ValidationError as exc:
        raise LeverSourceSchemaError("Lever response schema validation failed") from exc


def _checkpoint_equal(
    previous: Mapping[str, Mapping[str, str]],
    current: Mapping[str, Mapping[str, str]],
) -> bool:
    return {
        site_id: dict(values) for site_id, values in previous.items()
    } == {site_id: dict(values) for site_id, values in current.items()}

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from uuid import UUID

from pydantic import ValidationError

from cip.adapters.sources.recruitee.client import RecruiteeClient
from cip.adapters.sources.recruitee.mapper import (
    map_recruitee_offer,
    recruitee_offer_to_canonical,
)
from cip.adapters.sources.recruitee.registry import RecruiteeCareerSite
from cip.adapters.sources.recruitee.schemas import RecruiteeOffer, RecruiteeOffersResponse
from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    SourceRuntimeState,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc


class RecruiteeCollectionDeniedError(RuntimeError):
    """Source governance denied Recruitee careers collection."""


class RecruiteeSourceSchemaError(RuntimeError):
    """Recruitee payload no longer matches the approved public schema."""


class RecruiteeSourceWindowError(RuntimeError):
    """A Recruitee site exceeds the configured safe job count."""


@dataclass(frozen=True, slots=True)
class RecruiteeCheckpoint:
    fingerprints: Mapping[str, Mapping[str, str]]

    def __post_init__(self) -> None:
        copied = {
            site_id: MappingProxyType(dict(values))
            for site_id, values in self.fingerprints.items()
        }
        object.__setattr__(self, "fingerprints", MappingProxyType(copied))


@dataclass(frozen=True, slots=True)
class RecruiteeCollectionBatch:
    observations: tuple[RawObservation, ...]
    projections: tuple[CommercialProjection, ...]
    checkpoint: RecruiteeCheckpoint
    not_modified: bool


def collect_recruitee_jobs(
    client: RecruiteeClient,
    entry: SourceRegistryEntry,
    sites: tuple[RecruiteeCareerSite, ...],
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: RecruiteeCheckpoint | None = None,
    max_jobs_per_site: int = 5_000,
) -> RecruiteeCollectionBatch:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    enabled_sites = tuple(site for site in sites if site.enabled)
    if not enabled_sites:
        raise ValueError("at least one Recruitee site must be enabled")
    if max_jobs_per_site < 1:
        raise ValueError("max_jobs_per_site must be positive")
    previous = checkpoint.fingerprints if checkpoint else {}
    current: dict[str, dict[str, str]] = {}
    observations: list[RawObservation] = []
    projections: list[CommercialProjection] = []
    for site in enabled_sites:
        _authorize(entry, site.offers_url, collected_at=collected)
        offers = _parse_response(client.fetch_offers(site.offers_url).body).offers
        if len(offers) > max_jobs_per_site:
            raise RecruiteeSourceWindowError("Recruitee site exceeds configured job limit")
        current[site.id] = _collect_site(
            site,
            tuple(offers),
            previous=previous.get(site.id, {}),
            collection_job_id=collection_job_id,
            collected_at=collected,
            retention_until=retention_until,
            observations=observations,
            projections=projections,
        )
    current_checkpoint = RecruiteeCheckpoint(current)
    return RecruiteeCollectionBatch(
        observations=tuple(observations),
        projections=tuple(projections),
        checkpoint=current_checkpoint,
        not_modified=_checkpoint_equal(previous, current_checkpoint.fingerprints),
    )


def _collect_site(
    site: RecruiteeCareerSite,
    offers: tuple[RecruiteeOffer, ...],
    *,
    previous: Mapping[str, str],
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    observations: list[RawObservation],
    projections: list[CommercialProjection],
) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for offer in offers:
        key = offer.source_job_id
        if key in fingerprints:
            raise RecruiteeSourceSchemaError(f"duplicate offer id on site {site.id}: {key}")
        canonical = recruitee_offer_to_canonical(site, offer)
        fingerprint = canonical.fingerprint()
        fingerprints[key] = fingerprint
        mapped = map_recruitee_offer(
            site,
            offer,
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


def _authorize(
    entry: SourceRegistryEntry,
    target_url: str,
    *,
    collected_at: datetime,
) -> None:
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
        raise RecruiteeCollectionDeniedError(decision.reason.value)


def _parse_response(body: bytes) -> RecruiteeOffersResponse:
    try:
        return RecruiteeOffersResponse.model_validate_json(body)
    except ValidationError as exc:
        raise RecruiteeSourceSchemaError(
            "Recruitee response schema validation failed"
        ) from exc


def _checkpoint_equal(
    previous: Mapping[str, Mapping[str, str]],
    current: Mapping[str, Mapping[str, str]],
) -> bool:
    return {site_id: dict(values) for site_id, values in previous.items()} == {
        site_id: dict(values) for site_id, values in current.items()
    }

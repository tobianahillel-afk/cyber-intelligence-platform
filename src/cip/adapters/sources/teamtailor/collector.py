from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import ValidationError

from cip.adapters.sources.teamtailor.client import TeamtailorClient
from cip.adapters.sources.teamtailor.mapper import map_teamtailor_job, teamtailor_job_to_canonical
from cip.adapters.sources.teamtailor.registry import TeamtailorAccount
from cip.adapters.sources.teamtailor.schemas import TeamtailorJobResource, TeamtailorJobsResponse
from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import CollectionRequest, DataCategory, SourceRuntimeState
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc


class TeamtailorCollectionDeniedError(RuntimeError):
    pass


class TeamtailorSourceSchemaError(RuntimeError):
    pass


class TeamtailorSourceWindowError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TeamtailorCheckpoint:
    fingerprints: Mapping[str, Mapping[str, str]]

    def __post_init__(self) -> None:
        copied = {
            account_id: MappingProxyType(dict(values))
            for account_id, values in self.fingerprints.items()
        }
        object.__setattr__(self, "fingerprints", MappingProxyType(copied))


@dataclass(frozen=True, slots=True)
class TeamtailorCollectionBatch:
    observations: tuple[RawObservation, ...]
    projections: tuple[CommercialProjection, ...]
    checkpoint: TeamtailorCheckpoint
    not_modified: bool


def collect_teamtailor_jobs(
    client: TeamtailorClient,
    entry: SourceRegistryEntry,
    account: TeamtailorAccount,
    *,
    api_token: str,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: TeamtailorCheckpoint | None = None,
    max_jobs: int = 5_000,
) -> TeamtailorCollectionBatch:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    if not account.enabled:
        raise ValueError("Teamtailor account must be enabled")
    if max_jobs < 1:
        raise ValueError("max_jobs must be positive")
    previous = checkpoint.fingerprints if checkpoint else {}
    jobs = _fetch_public_jobs(
        client,
        entry,
        account,
        api_token=api_token,
        collected_at=collected,
        max_jobs=max_jobs,
    )
    observations: list[RawObservation] = []
    projections: list[CommercialProjection] = []
    fingerprints = _map_jobs(
        account,
        jobs,
        previous=previous.get(account.id, {}),
        collection_job_id=collection_job_id,
        collected_at=collected,
        retention_until=retention_until,
        observations=observations,
        projections=projections,
    )
    current = TeamtailorCheckpoint({account.id: fingerprints})
    return TeamtailorCollectionBatch(
        observations=tuple(observations),
        projections=tuple(projections),
        checkpoint=current,
        not_modified=_checkpoint_equal(previous, current.fingerprints),
    )


def _fetch_public_jobs(
    client: TeamtailorClient,
    entry: SourceRegistryEntry,
    account: TeamtailorAccount,
    *,
    api_token: str,
    collected_at: datetime,
    max_jobs: int,
) -> tuple[TeamtailorJobResource, ...]:
    jobs: list[TeamtailorJobResource] = []
    next_url: str | None = account.jobs_url
    visited: set[str] = set()
    while next_url is not None:
        if next_url in visited:
            raise TeamtailorSourceSchemaError("pagination loop detected")
        visited.add(next_url)
        _validate_jobs_url(account, next_url)
        _authorize(entry, next_url, collected_at=collected_at)
        page = _parse_response(
            client.fetch_jobs_page(
                next_url,
                api_token=api_token,
                api_version=account.api_version,
            ).body
        )
        jobs.extend(page.data)
        if len(jobs) > max_jobs:
            raise TeamtailorSourceWindowError("Teamtailor job limit exceeded")
        next_url = str(page.links.next) if page.links.next is not None else None
    return tuple(jobs)


def _map_jobs(
    account: TeamtailorAccount,
    jobs: tuple[TeamtailorJobResource, ...],
    *,
    previous: Mapping[str, str],
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    observations: list[RawObservation],
    projections: list[CommercialProjection],
) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for job in jobs:
        if job.id in fingerprints:
            raise TeamtailorSourceSchemaError(f"duplicate job id: {job.id}")
        canonical = teamtailor_job_to_canonical(account, job)
        fingerprint = canonical.fingerprint()
        fingerprints[job.id] = fingerprint
        mapped = map_teamtailor_job(
            account,
            job,
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
        )
        if mapped is not None:
            observation, projection = mapped
            projections.append(projection)
            if previous.get(job.id) != fingerprint:
                observations.append(observation)
    return fingerprints


def _validate_jobs_url(account: TeamtailorAccount, url: str) -> None:
    parsed = urlsplit(url)
    expected = urlsplit(account.base_url)
    if parsed.scheme != "https" or parsed.hostname != expected.hostname:
        raise TeamtailorSourceSchemaError("pagination URL outside provider host")
    if not parsed.path.startswith("/v1/jobs"):
        raise TeamtailorSourceSchemaError("pagination URL outside jobs endpoint")


def _authorize(entry: SourceRegistryEntry, url: str, *, collected_at: datetime) -> None:
    decision = entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.PUBLIC_JOB_POSTING,
            target_url=url,
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
        raise TeamtailorCollectionDeniedError(decision.reason.value)


def _parse_response(body: bytes) -> TeamtailorJobsResponse:
    try:
        return TeamtailorJobsResponse.model_validate_json(body)
    except ValidationError as exc:
        raise TeamtailorSourceSchemaError("Teamtailor schema validation failed") from exc


def _checkpoint_equal(
    previous: Mapping[str, Mapping[str, str]],
    current: Mapping[str, Mapping[str, str]],
) -> bool:
    return {key: dict(value) for key, value in previous.items()} == {
        key: dict(value) for key, value in current.items()
    }

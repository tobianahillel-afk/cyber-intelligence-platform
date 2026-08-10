from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from uuid import UUID

from pydantic import ValidationError

from cip.adapters.sources.ashby.client import AshbyClient
from cip.adapters.sources.ashby.mapper import ashby_job_to_canonical, map_ashby_job
from cip.adapters.sources.ashby.registry import AshbyBoard
from cip.adapters.sources.ashby.schemas import AshbyJobBoardResponse, AshbyJobPosting
from cip.adapters.sources.canonical_jobs import canonical_public_job_observation
from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    SourceRuntimeState,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc


class AshbyCollectionDeniedError(RuntimeError):
    """Source governance denied Ashby collection."""


class AshbySourceSchemaError(RuntimeError):
    """Ashby payload no longer matches the approved public schema."""


class AshbySourceWindowError(RuntimeError):
    """An Ashby board exceeds the configured safe job count."""


@dataclass(frozen=True, slots=True)
class AshbyCheckpoint:
    fingerprints: Mapping[str, Mapping[str, str]]

    def __post_init__(self) -> None:
        copied = {
            board_id: MappingProxyType(dict(values))
            for board_id, values in self.fingerprints.items()
        }
        object.__setattr__(self, "fingerprints", MappingProxyType(copied))


@dataclass(frozen=True, slots=True)
class AshbyCollectionBatch:
    observations: tuple[RawObservation, ...]
    projections: tuple[CommercialProjection, ...]
    checkpoint: AshbyCheckpoint
    not_modified: bool


def collect_ashby_jobs(
    client: AshbyClient,
    entry: SourceRegistryEntry,
    boards: tuple[AshbyBoard, ...],
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: AshbyCheckpoint | None = None,
    max_jobs_per_board: int = 5_000,
) -> AshbyCollectionBatch:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    enabled_boards = tuple(board for board in boards if board.enabled)
    if not enabled_boards:
        raise ValueError("at least one Ashby board must be enabled")
    if max_jobs_per_board < 1:
        raise ValueError("max_jobs_per_board must be positive")
    previous = checkpoint.fingerprints if checkpoint else {}
    current: dict[str, dict[str, str]] = {}
    observations: list[RawObservation] = []
    projections: list[CommercialProjection] = []
    for board in enabled_boards:
        _authorize(entry, client.board_url(board.board_name), collected_at=collected)
        jobs = _parse_response(client.fetch_jobs(board.board_name).body).jobs
        if len(jobs) > max_jobs_per_board:
            raise AshbySourceWindowError("Ashby board exceeds configured job limit")
        current[board.id] = _collect_board(
            board,
            tuple(job for job in jobs if job.is_listed),
            previous=previous.get(board.id, {}),
            collection_job_id=collection_job_id,
            collected_at=collected,
            retention_until=retention_until,
            observations=observations,
            projections=projections,
        )
    current_checkpoint = AshbyCheckpoint(current)
    return AshbyCollectionBatch(
        observations=tuple(observations),
        projections=tuple(projections),
        checkpoint=current_checkpoint,
        not_modified=_checkpoint_equal(previous, current_checkpoint.fingerprints),
    )


def _collect_board(
    board: AshbyBoard,
    jobs: tuple[AshbyJobPosting, ...],
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
        key = job.source_job_id
        if key in fingerprints:
            raise AshbySourceSchemaError(f"duplicate job id on board {board.id}: {key}")
        canonical = ashby_job_to_canonical(board, job)
        fingerprint = canonical.fingerprint()
        fingerprints[key] = fingerprint
        mapped = map_ashby_job(
            board,
            job,
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
        )
        if mapped is not None:
            observation, projection = mapped
            projections.append(projection)
        else:
            observation = canonical_public_job_observation(
                canonical,
                collection_job_id=collection_job_id,
                collected_at=collected_at,
                retention_until=retention_until,
            )
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
        raise AshbyCollectionDeniedError(decision.reason.value)


def _parse_response(body: bytes) -> AshbyJobBoardResponse:
    try:
        return AshbyJobBoardResponse.model_validate_json(body)
    except ValidationError as exc:
        raise AshbySourceSchemaError("Ashby response schema validation failed") from exc


def _checkpoint_equal(
    previous: Mapping[str, Mapping[str, str]],
    current: Mapping[str, Mapping[str, str]],
) -> bool:
    return {board_id: dict(values) for board_id, values in previous.items()} == {
        board_id: dict(values) for board_id, values in current.items()
    }

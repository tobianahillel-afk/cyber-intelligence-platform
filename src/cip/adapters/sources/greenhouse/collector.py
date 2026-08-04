from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Mapping
from uuid import UUID

from pydantic import ValidationError

from cip.adapters.sources.greenhouse.client import GreenhouseClient
from cip.adapters.sources.greenhouse.mapper import (
    greenhouse_job_fingerprint,
    map_greenhouse_job,
)
from cip.adapters.sources.greenhouse.registry import GreenhouseBoard
from cip.adapters.sources.greenhouse.schemas import GreenhouseJobsResponse
from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    SourceRuntimeState,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc


class GreenhouseCollectionDeniedError(RuntimeError):
    """Source governance denied Greenhouse collection."""


class GreenhouseSourceSchemaError(RuntimeError):
    """Greenhouse payload no longer matches the approved schema."""


class GreenhouseSourceWindowError(RuntimeError):
    """A Greenhouse board exceeds the configured safe job count."""


@dataclass(frozen=True, slots=True)
class GreenhouseCheckpoint:
    fingerprints: Mapping[str, Mapping[str, str]]

    def __post_init__(self) -> None:
        copied = {
            board_id: MappingProxyType(dict(values))
            for board_id, values in self.fingerprints.items()
        }
        object.__setattr__(self, "fingerprints", MappingProxyType(copied))


@dataclass(frozen=True, slots=True)
class GreenhouseCollectionBatch:
    observations: tuple[RawObservation, ...]
    projections: tuple[CommercialProjection, ...]
    checkpoint: GreenhouseCheckpoint
    not_modified: bool


def collect_greenhouse_jobs(
    client: GreenhouseClient,
    entry: SourceRegistryEntry,
    boards: tuple[GreenhouseBoard, ...],
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: GreenhouseCheckpoint | None = None,
    max_jobs_per_board: int = 5_000,
) -> GreenhouseCollectionBatch:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    enabled_boards = tuple(board for board in boards if board.enabled)
    if not enabled_boards:
        raise ValueError("at least one Greenhouse board must be enabled")
    if max_jobs_per_board < 1:
        raise ValueError("max_jobs_per_board must be positive")
    previous = checkpoint.fingerprints if checkpoint else {}
    current: dict[str, dict[str, str]] = {}
    observations: list[RawObservation] = []
    projections: list[CommercialProjection] = []

    for board in enabled_boards:
        _authorize(entry, client.jobs_url(board.board_token), collected_at=collected)
        response = _parse_response(client.fetch_jobs(board.board_token).body)
        _validate_job_window(response, max_jobs=max_jobs_per_board)
        board_fingerprints = _collect_board(
            board,
            response,
            previous=previous.get(board.id, {}),
            collection_job_id=collection_job_id,
            collected_at=collected,
            retention_until=retention_until,
            observations=observations,
            projections=projections,
        )
        current[board.id] = board_fingerprints

    current_checkpoint = GreenhouseCheckpoint(current)
    return GreenhouseCollectionBatch(
        observations=tuple(observations),
        projections=tuple(projections),
        checkpoint=current_checkpoint,
        not_modified=_checkpoint_equal(previous, current_checkpoint.fingerprints),
    )


def _collect_board(
    board: GreenhouseBoard,
    response: GreenhouseJobsResponse,
    *,
    previous: Mapping[str, str],
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    observations: list[RawObservation],
    projections: list[CommercialProjection],
) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for job in response.jobs:
        key = str(job.id)
        if key in fingerprints:
            raise GreenhouseSourceSchemaError(f"duplicate job id on board {board.id}: {key}")
        fingerprint = greenhouse_job_fingerprint(job)
        fingerprints[key] = fingerprint
        mapped = map_greenhouse_job(
            board,
            job,
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
        raise GreenhouseCollectionDeniedError(decision.reason.value)


def _parse_response(body: bytes) -> GreenhouseJobsResponse:
    try:
        return GreenhouseJobsResponse.model_validate_json(body)
    except ValidationError as exc:
        raise GreenhouseSourceSchemaError("Greenhouse response schema validation failed") from exc


def _validate_job_window(response: GreenhouseJobsResponse, *, max_jobs: int) -> None:
    total = response.meta.total if response.meta and response.meta.total is not None else len(response.jobs)
    if total > max_jobs or len(response.jobs) > max_jobs:
        raise GreenhouseSourceWindowError("Greenhouse board exceeds configured job limit")


def _checkpoint_equal(
    previous: Mapping[str, Mapping[str, str]],
    current: Mapping[str, Mapping[str, str]],
) -> bool:
    return {
        board_id: dict(values) for board_id, values in previous.items()
    } == {board_id: dict(values) for board_id, values in current.items()}

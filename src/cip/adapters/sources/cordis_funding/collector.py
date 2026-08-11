from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from urllib.parse import unquote, urlsplit
from uuid import UUID

from cip.adapters.sources.cordis_funding.client import CordisFundingClient
from cip.adapters.sources.cordis_funding.mapper import map_cordis_funding_record
from cip.adapters.sources.cordis_funding.parser import (
    MAX_RECORDS_PER_BATCH,
    CordisFundingArchiveError,
    CordisFundingSchemaError,
    parse_cordis_archive,
)
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


class CordisFundingPaginationError(RuntimeError):
    """CORDIS checkpoint state is unsafe."""


@dataclass(frozen=True, slots=True)
class CordisFundingCheckpoint:
    archive_sha256: str
    offset: int = 0
    complete: bool = False


@dataclass(frozen=True, slots=True)
class CordisFundingCollectionBatch:
    observations: tuple[RawObservation, ...]
    claims: tuple[ChangeClaimSnapshot, ...]
    checkpoint: CordisFundingCheckpoint
    not_modified: bool


def collect_cordis_funding(
    client: CordisFundingClient,
    entry: SourceRegistryEntry,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: CordisFundingCheckpoint | None = None,
    max_records: int = MAX_RECORDS_PER_BATCH,
) -> CordisFundingCollectionBatch:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    _validate_archive_url(entry, client.archive_url)
    _authorize(entry, client.archive_url, collected_at=collected)
    fetched = client.fetch()
    archive_hash = sha256(fetched.body).hexdigest()
    if checkpoint and checkpoint.archive_sha256 == archive_hash and checkpoint.complete:
        return CordisFundingCollectionBatch(
            observations=(), claims=(), checkpoint=checkpoint, not_modified=True
        )
    offset = _resolved_offset(checkpoint, archive_hash)
    parsed = parse_cordis_archive(fetched.body, offset=offset, max_records=max_records)
    mapped = [
        map_cordis_funding_record(
            record,
            collection_job_id=collection_job_id,
            collected_at=collected,
            retention_until=retention_until,
        )
        for record in parsed.records
    ]
    next_checkpoint = CordisFundingCheckpoint(
        archive_sha256=archive_hash,
        offset=parsed.next_offset,
        complete=not parsed.has_more,
    )
    return CordisFundingCollectionBatch(
        observations=tuple(item[0] for item in mapped),
        claims=tuple(item[1] for item in mapped),
        checkpoint=next_checkpoint,
        not_modified=not mapped,
    )


def _resolved_offset(
    checkpoint: CordisFundingCheckpoint | None,
    archive_hash: str,
) -> int:
    if checkpoint is None or checkpoint.archive_sha256 != archive_hash:
        return 0
    if checkpoint.offset < 0:
        raise CordisFundingPaginationError("CORDIS offset cannot be negative")
    return checkpoint.offset


def _validate_archive_url(entry: SourceRegistryEntry, url: str) -> None:
    parsed = urlsplit(url)
    base = urlsplit(entry.policy.base_url)
    if parsed.scheme != "https" or parsed.hostname != base.hostname:
        raise CordisFundingPaginationError("CORDIS URL outside provider host")
    if unquote(parsed.path) != unquote(base.path):
        raise CordisFundingPaginationError("CORDIS URL outside approved bulk path")


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


__all__ = [
    "CordisFundingArchiveError",
    "CordisFundingCheckpoint",
    "CordisFundingCollectionBatch",
    "CordisFundingCollectionDeniedError",
    "CordisFundingPaginationError",
    "CordisFundingSchemaError",
    "collect_cordis_funding",
]

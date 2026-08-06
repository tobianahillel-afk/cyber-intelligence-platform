from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import ValidationError

from cip.adapters.sources.cisa_kev.client import (
    CisaKevCheckpoint,
    CisaKevClient,
)
from cip.adapters.sources.cisa_kev.mapper import map_vulnerability
from cip.adapters.sources.cisa_kev.schemas import CisaKevCatalog
from cip.adapters.sources.cisa_kev.vulnerability_projection import (
    map_cisa_kev_vulnerability,
)
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    SourceRuntimeState,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.modules.vulnerability_knowledge.domain.models import VulnerabilitySnapshot
from cip.shared.kernel.time import require_aware_utc


class CollectionDeniedError(RuntimeError):
    """Source governance denied network collection."""


class SourceSchemaError(RuntimeError):
    """The source payload no longer matches the approved schema."""


@dataclass(frozen=True, slots=True)
class CisaKevCollectionBatch:
    observations: tuple[RawObservation, ...]
    vulnerability_snapshots: tuple[VulnerabilitySnapshot, ...]
    checkpoint: CisaKevCheckpoint
    not_modified: bool


def collect_cisa_kev(
    client: CisaKevClient,
    entry: SourceRegistryEntry,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: CisaKevCheckpoint | None = None,
) -> CisaKevCollectionBatch:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    decision = entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.VULNERABILITY_METADATA,
            target_url=entry.policy.base_url,
            purpose="vulnerability-intelligence",
            automated=True,
            store_raw_content=False,
            human_review_completed=False,
        ),
        entry.authorization,
        SourceRuntimeState(remaining_requests=1),
        now=collected,
    )
    if not decision.allowed:
        raise CollectionDeniedError(decision.reason.value)

    result = client.fetch(checkpoint)
    if result.not_modified:
        return CisaKevCollectionBatch(
            observations=(),
            vulnerability_snapshots=(),
            checkpoint=CisaKevCheckpoint(
                etag=result.etag,
                last_modified=result.last_modified,
                catalog_version=checkpoint.catalog_version if checkpoint else None,
            ),
            not_modified=True,
        )
    if result.body is None:
        raise SourceSchemaError("source returned no body for a modified response")
    try:
        catalog = CisaKevCatalog.model_validate_json(result.body)
    except ValidationError as exc:
        raise SourceSchemaError("CISA KEV schema validation failed") from exc
    observations = tuple(
        map_vulnerability(
            vulnerability,
            catalog,
            collection_job_id=collection_job_id,
            source_url=entry.policy.base_url,
            collected_at=collected,
            retention_until=retention_until,
        )
        for vulnerability in catalog.vulnerabilities
    )
    snapshots = tuple(
        map_cisa_kev_vulnerability(
            vulnerability,
            catalog,
            source_url=entry.policy.base_url,
        )
        for vulnerability in catalog.vulnerabilities
    )
    return CisaKevCollectionBatch(
        observations=observations,
        vulnerability_snapshots=snapshots,
        checkpoint=CisaKevCheckpoint(
            etag=result.etag,
            last_modified=result.last_modified,
            catalog_version=catalog.catalog_version,
        ),
        not_modified=False,
    )

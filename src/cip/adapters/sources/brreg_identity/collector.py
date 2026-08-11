from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from uuid import UUID

from pydantic import ValidationError

from cip.adapters.sources.brreg_identity.client import BrregIdentityClient
from cip.adapters.sources.brreg_identity.mapper import map_brreg_entity
from cip.adapters.sources.brreg_identity.schemas import BrregEntity
from cip.adapters.sources.organization_identity.registry import OrganizationIdentityTarget
from cip.modules.organizations.application.identity import IdentityProjection
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    SourceRuntimeState,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc


class BrregCollectionDeniedError(RuntimeError):
    """Source governance denied BRREG collection."""


class BrregSourceSchemaError(RuntimeError):
    """BRREG payload no longer matches the governed entity schema."""


@dataclass(frozen=True, slots=True)
class BrregCheckpoint:
    fingerprints: dict[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "fingerprints", MappingProxyType(dict(self.fingerprints)))


@dataclass(frozen=True, slots=True)
class BrregCollectionBatch:
    observations: tuple[RawObservation, ...]
    projections: tuple[IdentityProjection, ...]
    checkpoint: BrregCheckpoint
    not_modified: bool


def collect_brreg_entities(
    client: BrregIdentityClient,
    entry: SourceRegistryEntry,
    targets: tuple[OrganizationIdentityTarget, ...],
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: BrregCheckpoint | None = None,
) -> BrregCollectionBatch:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    previous = dict(checkpoint.fingerprints) if checkpoint else {}
    current = dict(previous)
    observations: list[RawObservation] = []
    projections: list[IdentityProjection] = []
    selected = tuple(
        target
        for target in targets
        if target.enabled
        and target.country_code == "NO"
        and target.foreign_registration is not None
    )
    for target in selected:
        registration = target.foreign_registration
        if registration is None:
            continue
        target_url = client.entity_url(registration)
        _authorize(entry, target_url, collected_at=collected)
        fetched = client.fetch_entity(registration)
        entity = _parse_entity(fetched.body)
        observation, projection, fingerprint = map_brreg_entity(
            target,
            entity,
            request_url=fetched.request_url,
            collection_job_id=collection_job_id,
            collected_at=collected,
            retention_until=retention_until,
        )
        current[target.id] = fingerprint
        if previous.get(target.id) == fingerprint:
            continue
        observations.append(observation)
        projections.append(projection)
    return BrregCollectionBatch(
        observations=tuple(observations),
        projections=tuple(projections),
        checkpoint=BrregCheckpoint(current),
        not_modified=not observations,
    )


def _authorize(
    entry: SourceRegistryEntry,
    target_url: str,
    *,
    collected_at: datetime,
) -> None:
    decision = entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.ORGANIZATION_METADATA,
            target_url=target_url,
            purpose="organization-identity-resolution",
            automated=True,
            store_raw_content=False,
            human_review_completed=False,
        ),
        entry.authorization,
        SourceRuntimeState(remaining_requests=1),
        now=collected_at,
    )
    if not decision.allowed:
        raise BrregCollectionDeniedError(decision.reason.value)


def _parse_entity(body: bytes) -> BrregEntity:
    try:
        return BrregEntity.model_validate_json(body)
    except ValidationError as exc:
        raise BrregSourceSchemaError("BRREG entity schema validation failed") from exc

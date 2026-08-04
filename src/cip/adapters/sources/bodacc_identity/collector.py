from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from uuid import UUID

from pydantic import ValidationError

from cip.adapters.sources.bodacc_identity.client import BodaccIdentityClient
from cip.adapters.sources.bodacc_identity.mapper import map_bodacc_identity
from cip.adapters.sources.bodacc_identity.schemas import BodaccIdentityResponse
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


class BodaccIdentityCollectionDeniedError(RuntimeError):
    pass


class BodaccIdentitySourceSchemaError(RuntimeError):
    pass


class BodaccIdentitySourceWindowError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class BodaccIdentityCheckpoint:
    fingerprints: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "fingerprints",
            MappingProxyType(dict(self.fingerprints)),
        )


@dataclass(frozen=True, slots=True)
class BodaccIdentityCollectionBatch:
    observations: tuple[RawObservation, ...]
    projections: tuple[IdentityProjection, ...]
    checkpoint: BodaccIdentityCheckpoint
    not_modified: bool


def collect_bodacc_identities(
    client: BodaccIdentityClient,
    entry: SourceRegistryEntry,
    targets: tuple[OrganizationIdentityTarget, ...],
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: BodaccIdentityCheckpoint | None = None,
    max_announcements_per_target: int = 100,
) -> BodaccIdentityCollectionBatch:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    enabled_targets = tuple(
        target
        for target in targets
        if target.enabled and target.country_code == "FR" and target.siren
    )
    if not enabled_targets:
        raise ValueError("at least one French identity target with SIREN must be enabled")
    if not 1 <= max_announcements_per_target <= 100:
        raise ValueError("max_announcements_per_target must be between 1 and 100")
    previous = checkpoint.fingerprints if checkpoint else {}
    current: dict[str, str] = {}
    observations: list[RawObservation] = []
    projections: list[IdentityProjection] = []
    for target in enabled_targets:
        assert target.siren is not None
        _authorize(entry, client.records_url, collected_at=collected)
        fetched = client.fetch_announcements(
            target.siren,
            limit=max_announcements_per_target,
        )
        response = _parse_response(fetched.body)
        if response.total_count > max_announcements_per_target:
            raise BodaccIdentitySourceWindowError(
                f"target {target.id} exceeds the configured BODACC history window"
            )
        mapped = map_bodacc_identity(
            target,
            tuple(response.results),
            request_url=fetched.request_url,
            collection_job_id=collection_job_id,
            collected_at=collected,
            retention_until=retention_until,
        )
        current[target.id] = mapped.fingerprint
        projections.append(mapped.projection)
        if previous.get(target.id) != mapped.fingerprint:
            observations.append(mapped.observation)
    current_checkpoint = BodaccIdentityCheckpoint(current)
    return BodaccIdentityCollectionBatch(
        observations=tuple(observations),
        projections=tuple(projections),
        checkpoint=current_checkpoint,
        not_modified=dict(previous) == dict(current_checkpoint.fingerprints),
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
        raise BodaccIdentityCollectionDeniedError(decision.reason.value)


def _parse_response(body: bytes) -> BodaccIdentityResponse:
    try:
        return BodaccIdentityResponse.model_validate_json(body)
    except ValidationError as exc:
        raise BodaccIdentitySourceSchemaError(
            "BODACC identity response schema validation failed"
        ) from exc

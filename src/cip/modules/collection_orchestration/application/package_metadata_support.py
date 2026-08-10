from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import httpx
from pydantic import BaseModel

from cip.adapters.sources.developer_ecosystem.mapper import map_public_metadata_resource
from cip.adapters.sources.developer_ecosystem.registry import (
    DeveloperEcosystemTarget,
    DeveloperTargetKind,
)
from cip.modules.collection_orchestration.application.intelligence_adapter_support import (
    IntelligenceObservationContext,
    authorize_intelligence_request,
    get_json,
    raw_intelligence_observation,
)
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.public_footprint.domain.models import (
    DiscoveryMethod,
    PublicResourceKind,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

PURPOSE = "developer-ecosystem-intelligence"


@dataclass(frozen=True, slots=True)
class PackageAdapterIdentity:
    source_id: str
    adapter_id: str
    adapter_version: str = "1"


@dataclass(frozen=True, slots=True)
class PackageProjectionInput:
    target: DeveloperEcosystemTarget
    source_url: str
    canonical_url: str
    title: str
    excerpt: str | None
    source_updated_at: datetime | None


def fetch_json(
    entry: SourceRegistryEntry,
    url: str,
    *,
    params: Mapping[str, str | int],
    collected_at: datetime,
    timeout_seconds: float,
    transport: httpx.BaseTransport | None,
) -> bytes:
    authorize_intelligence_request(
        entry,
        category=DataCategory.TECHNOLOGY_OBSERVATION,
        purpose=PURPOSE,
        target_url=url,
        collected_at=collected_at,
    )
    with httpx.Client(
        timeout=timeout_seconds,
        follow_redirects=False,
        transport=transport,
    ) as client:
        return get_json(
            client,
            url,
            headers={"Accept": "application/json"},
            params=params,
        )


def package_batch(
    record: BaseModel,
    projection_input: PackageProjectionInput,
    identity: PackageAdapterIdentity,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    next_index: int,
) -> AdapterCollectionBatch:
    target = projection_input.target
    projection = map_public_metadata_resource(
        record,
        organization_id=target.organization_id,
        source_id=identity.source_id,
        source_record_key=target.resource_identity,
        canonical_url=projection_input.canonical_url,
        source_url=projection_input.source_url,
        kind=PublicResourceKind.PACKAGE,
        discovery_method=DiscoveryMethod.PACKAGE_REGISTRY_API,
        collected_at=collected_at,
        title=projection_input.title,
        excerpt=projection_input.excerpt,
        source_updated_at=projection_input.source_updated_at,
    )
    context = IntelligenceObservationContext(
        source_id=identity.source_id,
        adapter_id=identity.adapter_id,
        adapter_version=identity.adapter_version,
        collection_job_id=collection_job_id,
        data_category=DataCategory.TECHNOLOGY_OBSERVATION,
        collected_at=collected_at,
        retention_until=retention_until,
    )
    observation = raw_intelligence_observation(
        record,
        context=context,
        source_url=projection_input.source_url,
        source_record_key=target.resource_identity,
        source_record_type="public-package-metadata",
        source_updated_at=projection_input.source_updated_at,
    )
    return AdapterCollectionBatch(
        observations=(observation,),
        public_footprint_projections=(projection,),
        checkpoint_payload={"target_index": next_index},
        not_modified=False,
    )


def next_target(
    targets: tuple[DeveloperEcosystemTarget, ...],
    payload: Mapping[str, object] | None,
) -> tuple[DeveloperEcosystemTarget | None, int]:
    if not targets:
        return None, 0
    value = 0 if payload is None else payload.get("target_index", 0)
    if not isinstance(value, int) or value < 0:
        raise AdapterExecutionError(
            "invalid package metadata checkpoint",
            error_code="invalid_checkpoint",
            retryable=False,
        )
    index = value % len(targets)
    next_index = 0 if index + 1 >= len(targets) else index + 1
    return targets[index], next_index


def targets_for_kind(
    targets: tuple[DeveloperEcosystemTarget, ...],
    kind: DeveloperTargetKind,
) -> tuple[DeveloperEcosystemTarget, ...]:
    return tuple(
        target for target in targets if target.enabled and target.kind is kind
    )


def require_entry(entry: SourceRegistryEntry, source_id: str) -> SourceRegistryEntry:
    if entry.policy.id != source_id:
        raise ValueError(f"adapter requires {source_id} policy")
    return entry


def require_timeout(value: float) -> float:
    if value <= 0:
        raise ValueError("timeout_seconds must be positive")
    return value


def version_excerpt(version: str | None, description: str | None) -> str | None:
    if version and description:
        return f"Latest public version {version}. {description}"[:1_000]
    if version:
        return f"Latest public version {version}"
    return description


def empty_package_batch() -> AdapterCollectionBatch:
    return AdapterCollectionBatch(
        observations=(),
        public_footprint_projections=(),
        checkpoint_payload={"target_index": 0},
        not_modified=True,
    )

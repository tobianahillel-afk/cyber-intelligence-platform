from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

import httpx

from cip.adapters.sources.developer_ecosystem.mapper import (
    PublicMetadataResourceInput,
    map_public_metadata_resource,
)
from cip.adapters.sources.developer_ecosystem.registry import (
    DeveloperEcosystemTarget,
    DeveloperTargetKind,
)
from cip.adapters.sources.developer_ecosystem.schemas import (
    GitHubRepositoryRecord,
    GitLabProjectRecord,
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
    PublicFootprintProjection,
    PublicResourceKind,
)
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

PAGE_SIZE = 100
MAX_CURSOR_TARGETS = 500
PURPOSE = "developer-ecosystem-intelligence"
GITHUB_SOURCE_ID = "github-public-org-repositories"
GITLAB_SOURCE_ID = "gitlab-public-group-projects"


def fetch_repository_json(
    entry: SourceRegistryEntry,
    url: str,
    *,
    params: Mapping[str, str | int],
    collected_at: datetime,
    timeout_seconds: float,
    transport: httpx.BaseTransport | None,
    headers: Mapping[str, str],
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
        return get_json(client, url, headers=headers, params=params)


def observation_context(
    *,
    source_id: str,
    adapter_id: str,
    adapter_version: str,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> IntelligenceObservationContext:
    return IntelligenceObservationContext(
        source_id=source_id,
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        collection_job_id=collection_job_id,
        data_category=DataCategory.TECHNOLOGY_OBSERVATION,
        collected_at=collected_at,
        retention_until=retention_until,
    )


def github_projection(
    record: GitHubRepositoryRecord,
    *,
    target: DeveloperEcosystemTarget,
    source_url: str,
    collected_at: datetime,
) -> PublicFootprintProjection:
    return map_public_metadata_resource(
        record,
        PublicMetadataResourceInput(
            organization_id=target.organization_id,
            source_id=GITHUB_SOURCE_ID,
            source_record_key=str(record.id),
            canonical_url=record.html_url,
            source_url=source_url,
            kind=PublicResourceKind.REPOSITORY,
            discovery_method=DiscoveryMethod.REPOSITORY_API,
            collected_at=collected_at,
            title=record.full_name,
            excerpt=record.description,
            source_updated_at=record.updated_at,
        ),
    )


def gitlab_projection(
    record: GitLabProjectRecord,
    *,
    target: DeveloperEcosystemTarget,
    source_url: str,
    collected_at: datetime,
) -> PublicFootprintProjection:
    return map_public_metadata_resource(
        record,
        PublicMetadataResourceInput(
            organization_id=target.organization_id,
            source_id=GITLAB_SOURCE_ID,
            source_record_key=str(record.id),
            canonical_url=record.web_url,
            source_url=source_url,
            kind=PublicResourceKind.REPOSITORY,
            discovery_method=DiscoveryMethod.REPOSITORY_API,
            collected_at=collected_at,
            title=record.path_with_namespace,
            excerpt=record.description,
            source_updated_at=record.last_activity_at,
        ),
    )


def github_observations(
    records: tuple[GitHubRepositoryRecord, ...],
    projections: tuple[PublicFootprintProjection, ...],
    *,
    context: IntelligenceObservationContext,
    source_url: str,
) -> tuple[RawObservation, ...]:
    allowed = {projection.resource.source_record_key for projection in projections}
    return tuple(
        raw_intelligence_observation(
            record,
            context=context,
            source_url=source_url,
            source_record_key=str(record.id),
            source_record_type="public-repository-metadata",
            source_updated_at=record.updated_at,
        )
        for record in records
        if str(record.id) in allowed
    )


def gitlab_observations(
    records: tuple[GitLabProjectRecord, ...],
    projections: tuple[PublicFootprintProjection, ...],
    *,
    context: IntelligenceObservationContext,
    source_url: str,
) -> tuple[RawObservation, ...]:
    allowed = {projection.resource.source_record_key for projection in projections}
    return tuple(
        raw_intelligence_observation(
            record,
            context=context,
            source_url=source_url,
            source_record_key=str(record.id),
            source_record_type="public-repository-metadata",
            source_updated_at=record.last_activity_at,
        )
        for record in records
        if str(record.id) in allowed
    )


def page_batch(
    observations: tuple[RawObservation, ...],
    projections: tuple[PublicFootprintProjection, ...],
    *,
    target: DeveloperEcosystemTarget,
    records_count: int,
    page: int,
    cursor: dict[str, int],
    targets: tuple[DeveloperEcosystemTarget, ...],
) -> AdapterCollectionBatch:
    next_index = _next_target_index(targets, target)
    if records_count >= PAGE_SIZE:
        cursor[target.target_id] = page + 1
        next_index = targets.index(target)
    else:
        cursor.pop(target.target_id, None)
    return AdapterCollectionBatch(
        observations=observations,
        public_footprint_projections=projections,
        checkpoint_payload={"target_index": next_index, "page_by_target": cursor},
        not_modified=not projections,
    )


def next_repository_target(
    targets: tuple[DeveloperEcosystemTarget, ...],
    payload: Mapping[str, object] | None,
) -> tuple[DeveloperEcosystemTarget | None, int, dict[str, int]]:
    if not targets:
        return None, 1, {}
    index = 0 if payload is None else payload.get("target_index", 0)
    if not isinstance(index, int) or index < 0:
        raise invalid_checkpoint_error()
    index %= len(targets)
    cursor = _cursor(payload, targets)
    target = targets[index]
    return target, cursor.get(target.target_id, 1), cursor


def enabled_targets(
    targets: tuple[DeveloperEcosystemTarget, ...],
    kind: DeveloperTargetKind,
) -> tuple[DeveloperEcosystemTarget, ...]:
    return tuple(
        target for target in targets if target.enabled and target.kind is kind
    )


def require_repository_entry(
    entry: SourceRegistryEntry,
    source_id: str,
) -> SourceRegistryEntry:
    if entry.policy.id != source_id:
        raise ValueError(f"adapter requires {source_id} policy")
    return entry


def require_repository_timeout(value: float) -> float:
    if value <= 0:
        raise ValueError("timeout_seconds must be positive")
    return value


def schema_error() -> AdapterExecutionError:
    return AdapterExecutionError(
        "developer repository response schema changed",
        error_code="source_schema_drift",
        retryable=False,
    )


def invalid_checkpoint_error() -> AdapterExecutionError:
    return AdapterExecutionError(
        "invalid developer repository checkpoint",
        error_code="invalid_checkpoint",
        retryable=False,
    )


def empty_repository_batch() -> AdapterCollectionBatch:
    return AdapterCollectionBatch(
        observations=(),
        public_footprint_projections=(),
        checkpoint_payload={"target_index": 0, "page_by_target": {}},
        not_modified=True,
    )


def _cursor(
    payload: Mapping[str, object] | None,
    targets: tuple[DeveloperEcosystemTarget, ...],
) -> dict[str, int]:
    raw = {} if payload is None else payload.get("page_by_target", {})
    if not isinstance(raw, dict) or len(raw) > MAX_CURSOR_TARGETS:
        raise invalid_checkpoint_error()
    known = {target.target_id for target in targets}
    result: dict[str, int] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, int) or value < 1:
            raise invalid_checkpoint_error()
        if key in known:
            result[key] = value
    return result


def _next_target_index(
    targets: tuple[DeveloperEcosystemTarget, ...],
    target: DeveloperEcosystemTarget,
) -> int:
    index = targets.index(target) + 1
    return 0 if index >= len(targets) else index

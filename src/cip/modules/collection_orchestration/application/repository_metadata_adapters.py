from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from urllib.parse import quote
from uuid import UUID

import httpx
from pydantic import TypeAdapter, ValidationError

from cip.adapters.sources.developer_ecosystem.mapper import map_public_metadata_resource
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

_PAGE_SIZE = 100
_MAX_CURSOR_TARGETS = 500
_PURPOSE = "developer-ecosystem-intelligence"
_GITHUB_LIST = TypeAdapter(list[GitHubRepositoryRecord])
_GITLAB_LIST = TypeAdapter(list[GitLabProjectRecord])


class GitHubOrganizationRepositoriesAdapter:
    source_id = "github-public-org-repositories"
    adapter_id = "github-org-repositories"
    adapter_version = "1"
    data_category = DataCategory.TECHNOLOGY_OBSERVATION

    def __init__(
        self,
        entry: SourceRegistryEntry,
        targets: tuple[DeveloperEcosystemTarget, ...],
        *,
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._entry = _entry(entry, self.source_id)
        self._targets = _targets(targets, DeveloperTargetKind.GITHUB_ORG)
        self._timeout_seconds = _timeout(timeout_seconds)
        self._transport = transport

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch:
        target, page, cursor = _next(self._targets, checkpoint_payload)
        if target is None:
            return _empty_batch()
        namespace = quote(target.namespace or "", safe="")
        url = f"{self._entry.policy.base_url}orgs/{namespace}/repos"
        records = self._fetch(
            url,
            params={
                "type": "public",
                "sort": "full_name",
                "direction": "asc",
                "per_page": _PAGE_SIZE,
                "page": page,
            },
            collected_at=collected_at,
        )
        projections = tuple(
            _github_projection(record, target=target, source_url=url, now=collected_at)
            for record in records
            if record.visibility.casefold() == "public"
        )
        observations = _github_observations(
            records,
            projections,
            context=_context(
                source_id=self.source_id,
                adapter_id=self.adapter_id,
                adapter_version=self.adapter_version,
                collection_job_id=collection_job_id,
                collected_at=collected_at,
                retention_until=retention_until,
            ),
            source_url=url,
        )
        return _page_batch(
            observations,
            projections,
            target=target,
            records_count=len(records),
            page=page,
            cursor=cursor,
            targets=self._targets,
        )

    def _fetch(
        self,
        url: str,
        *,
        params: Mapping[str, str | int],
        collected_at: datetime,
    ) -> tuple[GitHubRepositoryRecord, ...]:
        body = _fetch(
            self._entry,
            url,
            params=params,
            collected_at=collected_at,
            timeout_seconds=self._timeout_seconds,
            transport=self._transport,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2026-03-10",
            },
        )
        try:
            return tuple(_GITHUB_LIST.validate_json(body))
        except ValidationError as exc:
            raise _schema_error() from exc


class GitLabGroupProjectsAdapter:
    source_id = "gitlab-public-group-projects"
    adapter_id = "gitlab-group-projects"
    adapter_version = "1"
    data_category = DataCategory.TECHNOLOGY_OBSERVATION

    def __init__(
        self,
        entry: SourceRegistryEntry,
        targets: tuple[DeveloperEcosystemTarget, ...],
        *,
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._entry = _entry(entry, self.source_id)
        self._targets = _targets(targets, DeveloperTargetKind.GITLAB_GROUP)
        self._timeout_seconds = _timeout(timeout_seconds)
        self._transport = transport

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch:
        target, page, cursor = _next(self._targets, checkpoint_payload)
        if target is None:
            return _empty_batch()
        namespace = quote(target.namespace or "", safe="")
        url = f"{self._entry.policy.base_url}groups/{namespace}/projects"
        records = self._fetch(
            url,
            params={
                "visibility": "public",
                "simple": "true",
                "order_by": "id",
                "sort": "asc",
                "per_page": _PAGE_SIZE,
                "page": page,
            },
            collected_at=collected_at,
        )
        projections = tuple(
            _gitlab_projection(record, target=target, source_url=url, now=collected_at)
            for record in records
            if record.visibility.casefold() == "public"
        )
        observations = _gitlab_observations(
            records,
            projections,
            context=_context(
                source_id=self.source_id,
                adapter_id=self.adapter_id,
                adapter_version=self.adapter_version,
                collection_job_id=collection_job_id,
                collected_at=collected_at,
                retention_until=retention_until,
            ),
            source_url=url,
        )
        return _page_batch(
            observations,
            projections,
            target=target,
            records_count=len(records),
            page=page,
            cursor=cursor,
            targets=self._targets,
        )

    def _fetch(
        self,
        url: str,
        *,
        params: Mapping[str, str | int],
        collected_at: datetime,
    ) -> tuple[GitLabProjectRecord, ...]:
        body = _fetch(
            self._entry,
            url,
            params=params,
            collected_at=collected_at,
            timeout_seconds=self._timeout_seconds,
            transport=self._transport,
            headers={"Accept": "application/json"},
        )
        try:
            return tuple(_GITLAB_LIST.validate_json(body))
        except ValidationError as exc:
            raise _schema_error() from exc


def _github_projection(
    record: GitHubRepositoryRecord,
    *,
    target: DeveloperEcosystemTarget,
    source_url: str,
    now: datetime,
) -> PublicFootprintProjection:
    return map_public_metadata_resource(
        record,
        organization_id=target.organization_id,
        source_id=GitHubOrganizationRepositoriesAdapter.source_id,
        source_record_key=str(record.id),
        canonical_url=record.html_url,
        source_url=source_url,
        kind=PublicResourceKind.REPOSITORY,
        discovery_method=DiscoveryMethod.REPOSITORY_API,
        collected_at=now,
        title=record.full_name,
        excerpt=record.description,
        source_updated_at=record.updated_at,
    )


def _gitlab_projection(
    record: GitLabProjectRecord,
    *,
    target: DeveloperEcosystemTarget,
    source_url: str,
    now: datetime,
) -> PublicFootprintProjection:
    return map_public_metadata_resource(
        record,
        organization_id=target.organization_id,
        source_id=GitLabGroupProjectsAdapter.source_id,
        source_record_key=str(record.id),
        canonical_url=record.web_url,
        source_url=source_url,
        kind=PublicResourceKind.REPOSITORY,
        discovery_method=DiscoveryMethod.REPOSITORY_API,
        collected_at=now,
        title=record.path_with_namespace,
        excerpt=record.description,
        source_updated_at=record.last_activity_at,
    )


def _github_observations(
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


def _gitlab_observations(
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


def _fetch(
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
        purpose=_PURPOSE,
        target_url=url,
        collected_at=collected_at,
    )
    with httpx.Client(
        timeout=timeout_seconds,
        follow_redirects=False,
        transport=transport,
    ) as client:
        return get_json(client, url, headers=headers, params=params)


def _context(
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


def _page_batch(
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
    if records_count >= _PAGE_SIZE:
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


def _next(
    targets: tuple[DeveloperEcosystemTarget, ...],
    payload: Mapping[str, object] | None,
) -> tuple[DeveloperEcosystemTarget | None, int, dict[str, int]]:
    if not targets:
        return None, 1, {}
    index = 0 if payload is None else payload.get("target_index", 0)
    if not isinstance(index, int) or index < 0:
        raise _invalid_checkpoint()
    index %= len(targets)
    cursor = _cursor(payload, targets)
    target = targets[index]
    return target, cursor.get(target.target_id, 1), cursor


def _cursor(
    payload: Mapping[str, object] | None,
    targets: tuple[DeveloperEcosystemTarget, ...],
) -> dict[str, int]:
    raw = {} if payload is None else payload.get("page_by_target", {})
    if not isinstance(raw, dict) or len(raw) > _MAX_CURSOR_TARGETS:
        raise _invalid_checkpoint()
    known = {target.target_id for target in targets}
    result: dict[str, int] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, int) or value < 1:
            raise _invalid_checkpoint()
        if key in known:
            result[key] = value
    return result


def _next_target_index(
    targets: tuple[DeveloperEcosystemTarget, ...],
    target: DeveloperEcosystemTarget,
) -> int:
    index = targets.index(target) + 1
    return 0 if index >= len(targets) else index


def _targets(
    targets: tuple[DeveloperEcosystemTarget, ...],
    kind: DeveloperTargetKind,
) -> tuple[DeveloperEcosystemTarget, ...]:
    return tuple(
        target for target in targets if target.enabled and target.kind is kind
    )


def _entry(entry: SourceRegistryEntry, source_id: str) -> SourceRegistryEntry:
    if entry.policy.id != source_id:
        raise ValueError(f"adapter requires {source_id} policy")
    return entry


def _timeout(value: float) -> float:
    if value <= 0:
        raise ValueError("timeout_seconds must be positive")
    return value


def _schema_error() -> AdapterExecutionError:
    return AdapterExecutionError(
        "developer repository response schema changed",
        error_code="source_schema_drift",
        retryable=False,
    )


def _invalid_checkpoint() -> AdapterExecutionError:
    return AdapterExecutionError(
        "invalid developer repository checkpoint",
        error_code="invalid_checkpoint",
        retryable=False,
    )


def _empty_batch() -> AdapterCollectionBatch:
    return AdapterCollectionBatch(
        observations=(),
        public_footprint_projections=(),
        checkpoint_payload={"target_index": 0, "page_by_target": {}},
        not_modified=True,
    )

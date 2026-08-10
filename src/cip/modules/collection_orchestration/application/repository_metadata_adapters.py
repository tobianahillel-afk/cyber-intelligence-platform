from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from urllib.parse import quote
from uuid import UUID

import httpx
from pydantic import TypeAdapter, ValidationError

from cip.adapters.sources.developer_ecosystem.registry import (
    DeveloperEcosystemTarget,
    DeveloperTargetKind,
)
from cip.adapters.sources.developer_ecosystem.schemas import (
    GitHubRepositoryRecord,
    GitLabProjectRecord,
)
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
)
from cip.modules.collection_orchestration.application.repository_metadata_support import (
    GITHUB_SOURCE_ID,
    GITLAB_SOURCE_ID,
    PAGE_SIZE,
    empty_repository_batch,
    enabled_targets,
    fetch_repository_json,
    github_observations,
    github_projection,
    gitlab_observations,
    gitlab_projection,
    next_repository_target,
    observation_context,
    page_batch,
    require_repository_entry,
    require_repository_timeout,
    schema_error,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_GITHUB_LIST = TypeAdapter(list[GitHubRepositoryRecord])
_GITLAB_LIST = TypeAdapter(list[GitLabProjectRecord])


class GitHubOrganizationRepositoriesAdapter:
    source_id = GITHUB_SOURCE_ID
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
        self._entry = require_repository_entry(entry, self.source_id)
        self._targets = enabled_targets(targets, DeveloperTargetKind.GITHUB_ORG)
        self._timeout_seconds = require_repository_timeout(timeout_seconds)
        self._transport = transport

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch:
        target, page, cursor = next_repository_target(
            self._targets,
            checkpoint_payload,
        )
        if target is None:
            return empty_repository_batch()
        namespace = quote(target.namespace or "", safe="")
        url = f"{self._entry.policy.base_url}orgs/{namespace}/repos"
        records = self._fetch(url, page=page, collected_at=collected_at)
        projections = tuple(
            github_projection(
                record,
                target=target,
                source_url=url,
                collected_at=collected_at,
            )
            for record in records
            if record.visibility.casefold() == "public"
        )
        observations = github_observations(
            records,
            projections,
            context=observation_context(
                source_id=self.source_id,
                adapter_id=self.adapter_id,
                adapter_version=self.adapter_version,
                collection_job_id=collection_job_id,
                collected_at=collected_at,
                retention_until=retention_until,
            ),
            source_url=url,
        )
        return page_batch(
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
        page: int,
        collected_at: datetime,
    ) -> tuple[GitHubRepositoryRecord, ...]:
        body = fetch_repository_json(
            self._entry,
            url,
            params={
                "type": "public",
                "sort": "full_name",
                "direction": "asc",
                "per_page": PAGE_SIZE,
                "page": page,
            },
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
            raise schema_error() from exc


class GitLabGroupProjectsAdapter:
    source_id = GITLAB_SOURCE_ID
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
        self._entry = require_repository_entry(entry, self.source_id)
        self._targets = enabled_targets(targets, DeveloperTargetKind.GITLAB_GROUP)
        self._timeout_seconds = require_repository_timeout(timeout_seconds)
        self._transport = transport

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch:
        target, page, cursor = next_repository_target(
            self._targets,
            checkpoint_payload,
        )
        if target is None:
            return empty_repository_batch()
        namespace = quote(target.namespace or "", safe="")
        url = f"{self._entry.policy.base_url}groups/{namespace}/projects"
        records = self._fetch(url, page=page, collected_at=collected_at)
        projections = tuple(
            gitlab_projection(
                record,
                target=target,
                source_url=url,
                collected_at=collected_at,
            )
            for record in records
            if record.visibility.casefold() == "public"
        )
        observations = gitlab_observations(
            records,
            projections,
            context=observation_context(
                source_id=self.source_id,
                adapter_id=self.adapter_id,
                adapter_version=self.adapter_version,
                collection_job_id=collection_job_id,
                collected_at=collected_at,
                retention_until=retention_until,
            ),
            source_url=url,
        )
        return page_batch(
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
        page: int,
        collected_at: datetime,
    ) -> tuple[GitLabProjectRecord, ...]:
        body = fetch_repository_json(
            self._entry,
            url,
            params={
                "visibility": "public",
                "simple": "true",
                "order_by": "id",
                "sort": "asc",
                "per_page": PAGE_SIZE,
                "page": page,
            },
            collected_at=collected_at,
            timeout_seconds=self._timeout_seconds,
            transport=self._transport,
            headers={"Accept": "application/json"},
        )
        try:
            return tuple(_GITLAB_LIST.validate_json(body))
        except ValidationError as exc:
            raise schema_error() from exc

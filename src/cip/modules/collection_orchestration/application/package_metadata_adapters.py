from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from urllib.parse import quote
from uuid import UUID

import httpx
from pydantic import ValidationError

from cip.adapters.sources.developer_ecosystem.mapper import map_public_metadata_resource
from cip.adapters.sources.developer_ecosystem.registry import (
    DeveloperEcosystemTarget,
    DeveloperTargetKind,
)
from cip.adapters.sources.developer_ecosystem.schemas import (
    MavenSearchResponse,
    NpmPackageRecord,
    PyPiProjectRecord,
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
from cip.modules.public_footprint.domain.models import DiscoveryMethod, PublicResourceKind
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_PURPOSE = "developer-ecosystem-intelligence"


class PyPiPackageAdapter:
    source_id = "pypi-public-package-metadata"
    adapter_id = "pypi-project-json"
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
        self._targets = _targets(targets, DeveloperTargetKind.PYPI_PACKAGE)
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
        target, next_index = _next_target(self._targets, checkpoint_payload)
        if target is None:
            return _empty_batch()
        name = quote(target.name or "", safe="-_.")
        url = f"{self._entry.policy.base_url}pypi/{name}/json"
        record = _fetch_model(
            self._entry,
            url,
            PyPiProjectRecord,
            collected_at=collected_at,
            timeout_seconds=self._timeout_seconds,
            transport=self._transport,
        )
        canonical_url = f"https://pypi.org/project/{quote(record.info.name, safe='-_.')}/"
        return _package_batch(
            record,
            target=target,
            adapter=self,
            source_url=url,
            canonical_url=canonical_url,
            title=record.info.name,
            excerpt=_version_excerpt(record.info.version, record.info.summary),
            source_updated_at=None,
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
            next_index=next_index,
        )


class NpmPackageAdapter:
    source_id = "npm-public-package-metadata"
    adapter_id = "npm-package-metadata"
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
        self._targets = _targets(targets, DeveloperTargetKind.NPM_PACKAGE)
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
        target, next_index = _next_target(self._targets, checkpoint_payload)
        if target is None:
            return _empty_batch()
        name = target.name or ""
        url = f"{self._entry.policy.base_url}{quote(name, safe='@-_.')}"
        record = _fetch_model(
            self._entry,
            url,
            NpmPackageRecord,
            collected_at=collected_at,
            timeout_seconds=self._timeout_seconds,
            transport=self._transport,
        )
        canonical_url = f"https://www.npmjs.com/package/{quote(record.name, safe='@/-_.')}"
        return _package_batch(
            record,
            target=target,
            adapter=self,
            source_url=url,
            canonical_url=canonical_url,
            title=record.name,
            excerpt=_version_excerpt(record.latest_version, record.description),
            source_updated_at=record.modified,
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
            next_index=next_index,
        )


class MavenCentralArtifactAdapter:
    source_id = "maven-central-public-metadata"
    adapter_id = "maven-central-search"
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
        self._targets = _targets(targets, DeveloperTargetKind.MAVEN_ARTIFACT)
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
        target, next_index = _next_target(self._targets, checkpoint_payload)
        if target is None:
            return _empty_batch()
        group_id = target.namespace or ""
        artifact_id = target.name or ""
        url = self._entry.policy.base_url
        query = f'g:"{group_id}" AND a:"{artifact_id}"'
        response = _fetch_maven(
            self._entry,
            url,
            query=query,
            collected_at=collected_at,
            timeout_seconds=self._timeout_seconds,
            transport=self._transport,
        )
        records = [
            record
            for record in response.response.docs
            if record.g == group_id and record.a == artifact_id
        ]
        if len(records) != 1:
            raise AdapterExecutionError(
                "Maven Central response does not contain one exact artifact",
                error_code="source_identity_mismatch",
                retryable=False,
            )
        record = records[0]
        canonical_url = (
            "https://central.sonatype.com/artifact/"
            f"{quote(record.g, safe='.-')}/{quote(record.a, safe='.-')}"
        )
        updated_at = datetime.fromtimestamp(record.timestamp / 1000, tz=UTC)
        return _package_batch(
            record,
            target=target,
            adapter=self,
            source_url=url,
            canonical_url=canonical_url,
            title=f"{record.g}:{record.a}",
            excerpt=f"Latest public version {record.latestVersion}",
            source_updated_at=updated_at,
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
            next_index=next_index,
        )


def _fetch_model(
    entry: SourceRegistryEntry,
    url: str,
    model_type: type[PyPiProjectRecord] | type[NpmPackageRecord],
    *,
    collected_at: datetime,
    timeout_seconds: float,
    transport: httpx.BaseTransport | None,
):
    body = _fetch_json(
        entry,
        url,
        params={},
        collected_at=collected_at,
        timeout_seconds=timeout_seconds,
        transport=transport,
    )
    try:
        return model_type.model_validate_json(body)
    except ValidationError as exc:
        raise AdapterExecutionError(
            "package metadata response schema changed",
            error_code="source_schema_drift",
            retryable=False,
        ) from exc


def _fetch_maven(
    entry: SourceRegistryEntry,
    url: str,
    *,
    query: str,
    collected_at: datetime,
    timeout_seconds: float,
    transport: httpx.BaseTransport | None,
) -> MavenSearchResponse:
    body = _fetch_json(
        entry,
        url,
        params={"q": query, "rows": 1, "wt": "json"},
        collected_at=collected_at,
        timeout_seconds=timeout_seconds,
        transport=transport,
    )
    try:
        return MavenSearchResponse.model_validate_json(body)
    except ValidationError as exc:
        raise AdapterExecutionError(
            "Maven Central response schema changed",
            error_code="source_schema_drift",
            retryable=False,
        ) from exc


def _fetch_json(
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
        purpose=_PURPOSE,
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


def _package_batch(
    record,
    *,
    target: DeveloperEcosystemTarget,
    adapter,
    source_url: str,
    canonical_url: str,
    title: str,
    excerpt: str | None,
    source_updated_at: datetime | None,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    next_index: int,
) -> AdapterCollectionBatch:
    projection = map_public_metadata_resource(
        record,
        organization_id=target.organization_id,
        source_id=adapter.source_id,
        source_record_key=target.resource_identity,
        canonical_url=canonical_url,
        source_url=source_url,
        kind=PublicResourceKind.PACKAGE,
        discovery_method=DiscoveryMethod.PACKAGE_REGISTRY_API,
        collected_at=collected_at,
        title=title,
        excerpt=excerpt,
        source_updated_at=source_updated_at,
    )
    context = IntelligenceObservationContext(
        source_id=adapter.source_id,
        adapter_id=adapter.adapter_id,
        adapter_version=adapter.adapter_version,
        collection_job_id=collection_job_id,
        data_category=DataCategory.TECHNOLOGY_OBSERVATION,
        collected_at=collected_at,
        retention_until=retention_until,
    )
    observation = raw_intelligence_observation(
        record,
        context=context,
        source_url=source_url,
        source_record_key=target.resource_identity,
        source_record_type="public-package-metadata",
        source_updated_at=source_updated_at,
    )
    return AdapterCollectionBatch(
        observations=(observation,),
        public_footprint_projections=(projection,),
        checkpoint_payload={"target_index": next_index},
        not_modified=False,
    )


def _next_target(
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


def _targets(
    targets: tuple[DeveloperEcosystemTarget, ...],
    kind: DeveloperTargetKind,
) -> tuple[DeveloperEcosystemTarget, ...]:
    return tuple(target for target in targets if target.enabled and target.kind is kind)


def _entry(entry: SourceRegistryEntry, source_id: str) -> SourceRegistryEntry:
    if entry.policy.id != source_id:
        raise ValueError(f"adapter requires {source_id} policy")
    return entry


def _timeout(value: float) -> float:
    if value <= 0:
        raise ValueError("timeout_seconds must be positive")
    return value


def _version_excerpt(version: str | None, description: str | None) -> str | None:
    if version and description:
        return f"Latest public version {version}. {description}"[:1_000]
    if version:
        return f"Latest public version {version}"
    return description


def _empty_batch() -> AdapterCollectionBatch:
    return AdapterCollectionBatch(
        observations=(),
        public_footprint_projections=(),
        checkpoint_payload={"target_index": 0},
        not_modified=True,
    )

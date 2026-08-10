from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from urllib.parse import urlencode
from uuid import UUID

import httpx
from pydantic import ValidationError

from cip.adapters.sources.developer_ecosystem.registry import (
    DeveloperEcosystemTarget,
    DeveloperTargetKind,
)
from cip.adapters.sources.developer_ecosystem.schemas import MavenSearchResponse
from cip.modules.collection_orchestration.application.package_metadata_support import (
    PackageAdapterIdentity,
    PackageProjectionInput,
    empty_package_batch,
    fetch_json,
    next_target,
    package_batch,
    require_entry,
    require_timeout,
    targets_for_kind,
)
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


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
        self._entry = require_entry(entry, self.source_id)
        self._targets = targets_for_kind(targets, DeveloperTargetKind.MAVEN_ARTIFACT)
        self._timeout_seconds = require_timeout(timeout_seconds)
        self._transport = transport

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch:
        target, next_index = next_target(self._targets, checkpoint_payload)
        if target is None:
            return empty_package_batch()
        group_id = target.namespace or ""
        artifact_id = target.name or ""
        query = f'g:"{group_id}" AND a:"{artifact_id}"'
        params: dict[str, str | int] = {"q": query, "rows": 1, "wt": "json"}
        body = fetch_json(
            self._entry,
            self._entry.policy.base_url,
            params=params,
            collected_at=collected_at,
            timeout_seconds=self._timeout_seconds,
            transport=self._transport,
        )
        try:
            response = MavenSearchResponse.model_validate_json(body)
        except ValidationError as exc:
            raise _schema_error() from exc
        records = tuple(
            record
            for record in response.response.docs
            if record.g == group_id and record.a == artifact_id
        )
        if len(records) != 1:
            raise _identity_error()
        record = records[0]
        source_url = f"{self._entry.policy.base_url}?{urlencode(params)}"
        canonical_url = (
            "https://central.sonatype.com/artifact/"
            f"{record.g}/{record.a}"
        )
        updated_at = datetime.fromtimestamp(record.timestamp / 1000, tz=UTC)
        return package_batch(
            record,
            PackageProjectionInput(
                target=target,
                source_url=source_url,
                canonical_url=canonical_url,
                title=f"{record.g}:{record.a}",
                excerpt=f"Latest public version {record.latestVersion}",
                source_updated_at=updated_at,
            ),
            PackageAdapterIdentity(self.source_id, self.adapter_id),
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
            next_index=next_index,
        )


def _schema_error() -> AdapterExecutionError:
    return AdapterExecutionError(
        "Maven Central response schema changed",
        error_code="source_schema_drift",
        retryable=False,
    )


def _identity_error() -> AdapterExecutionError:
    return AdapterExecutionError(
        "Maven Central response does not contain one exact artifact",
        error_code="source_identity_mismatch",
        retryable=False,
    )

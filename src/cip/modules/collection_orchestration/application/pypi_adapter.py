from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from urllib.parse import quote
from uuid import UUID

import httpx
from pydantic import ValidationError

from cip.adapters.sources.developer_ecosystem.registry import (
    DeveloperEcosystemTarget,
    DeveloperTargetKind,
)
from cip.adapters.sources.developer_ecosystem.schemas import PyPiProjectRecord
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
    version_excerpt,
)
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


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
        self._entry = require_entry(entry, self.source_id)
        self._targets = targets_for_kind(targets, DeveloperTargetKind.PYPI_PACKAGE)
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
        name = quote(target.name or "", safe="-_.")
        source_url = f"{self._entry.policy.base_url}pypi/{name}/json"
        body = fetch_json(
            self._entry,
            source_url,
            params={},
            collected_at=collected_at,
            timeout_seconds=self._timeout_seconds,
            transport=self._transport,
        )
        try:
            record = PyPiProjectRecord.model_validate_json(body)
        except ValidationError as exc:
            raise _schema_error() from exc
        if record.info.name.casefold() != (target.name or "").casefold():
            raise _identity_error()
        canonical_url = (
            f"https://pypi.org/project/{quote(record.info.name, safe='-_.')}/"
        )
        return package_batch(
            record,
            PackageProjectionInput(
                target=target,
                source_url=source_url,
                canonical_url=canonical_url,
                title=record.info.name,
                excerpt=version_excerpt(record.info.version, record.info.summary),
                source_updated_at=None,
            ),
            PackageAdapterIdentity(self.source_id, self.adapter_id),
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
            next_index=next_index,
        )


def _schema_error() -> AdapterExecutionError:
    return AdapterExecutionError(
        "PyPI response schema changed",
        error_code="source_schema_drift",
        retryable=False,
    )


def _identity_error() -> AdapterExecutionError:
    return AdapterExecutionError(
        "PyPI response does not match requested package",
        error_code="source_identity_mismatch",
        retryable=False,
    )

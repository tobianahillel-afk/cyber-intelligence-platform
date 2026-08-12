from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

import httpx

from cip.adapters.sources.public_web.client import (
    PublicWebClient,
    PublicWebPolicyDeniedError,
    PublicWebResponseError,
)
from cip.adapters.sources.public_web.collection_policy import PublicWebCollectionDeniedError
from cip.adapters.sources.public_web.collector import (
    PageCheckpoint,
    PublicWebCheckpoint,
    collect_public_web_target,
)
from cip.adapters.sources.public_web.parsing import PublicWebParseError
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.public_footprint.domain import PublicResourceKind
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


class PublicWebAdapter:
    adapter_id = "public-web-sitemap"
    data_category = DataCategory.OFFICIAL_DOCUMENT_DISCOVERY

    def __init__(
        self,
        entry: SourceRegistryEntry,
        target: PublicWebTarget,
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._entry = entry
        self._target = target
        self._timeout_seconds = timeout_seconds

    @property
    def target_id(self) -> str:
        return self._target.id

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch:
        checkpoint = _parse_checkpoint(checkpoint_payload)
        try:
            with httpx.Client(timeout=self._timeout_seconds) as http_client:
                batch = collect_public_web_target(
                    PublicWebClient(http_client),
                    self._entry,
                    self._target,
                    collection_job_id=collection_job_id,
                    collected_at=collected_at,
                    retention_until=retention_until,
                    checkpoint=checkpoint,
                )
        except (
            httpx.HTTPError,
            PublicWebCollectionDeniedError,
            PublicWebParseError,
            PublicWebPolicyDeniedError,
            PublicWebResponseError,
        ) as exc:
            raise AdapterExecutionError(str(exc)) from exc
        return AdapterCollectionBatch(
            observations=batch.observations,
            public_footprint_projections=batch.projections,
            checkpoint_payload=_checkpoint_payload(batch.checkpoint),
            not_modified=batch.not_modified,
        )


def _parse_checkpoint(payload: Mapping[str, object] | None) -> PublicWebCheckpoint | None:
    if payload is None:
        return None
    raw_pages = payload.get("pages")
    if not isinstance(raw_pages, dict):
        raise AdapterExecutionError("public-web checkpoint pages must be a mapping")
    pages: dict[str, PageCheckpoint] = {}
    for raw_url, raw_page in raw_pages.items():
        if not isinstance(raw_url, str) or not isinstance(raw_page, dict):
            raise AdapterExecutionError("public-web checkpoint page is invalid")
        try:
            raw_kind = raw_page.get("resource_kind", PublicResourceKind.WEB_PAGE.value)
            pages[raw_url] = PageCheckpoint(
                content_hash_sha256=_required_string(raw_page, "content_hash_sha256"),
                version_id=UUID(_required_string(raw_page, "version_id")),
                canonical_url=_required_string(raw_page, "canonical_url"),
                resource_kind=PublicResourceKind(_required_string_value(raw_kind)),
            )
        except (TypeError, ValueError) as exc:
            raise AdapterExecutionError("public-web checkpoint page is invalid") from exc
    return PublicWebCheckpoint(pages)


def _checkpoint_payload(checkpoint: PublicWebCheckpoint) -> dict[str, object]:
    return {
        "pages": {
            url: {
                "content_hash_sha256": page.content_hash_sha256,
                "version_id": str(page.version_id),
                "canonical_url": page.canonical_url,
                "resource_kind": page.resource_kind.value,
            }
            for url, page in checkpoint.pages.items()
        }
    }


def _required_string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _required_string_value(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("resource_kind must be a non-empty string")
    return value

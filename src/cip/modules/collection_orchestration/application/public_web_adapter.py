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
from cip.adapters.sources.public_web.collector import (
    PageCheckpoint,
    PublicWebCheckpoint,
    PublicWebCollectionDeniedError,
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
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if entry.policy.id != target.id:
            raise ValueError("public web adapter requires matching source and target ids")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.source_id = target.id
        self._entry = entry
        self._target = target
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch:
        checkpoint = _checkpoint_from_payload(checkpoint_payload)
        try:
            with httpx.Client(
                timeout=self._timeout_seconds,
                follow_redirects=False,
                transport=self._transport,
            ) as http_client:
                batch = collect_public_web_target(
                    PublicWebClient(http_client),
                    self._entry,
                    self._target,
                    collection_job_id=collection_job_id,
                    collected_at=collected_at,
                    retention_until=retention_until,
                    checkpoint=checkpoint,
                )
        except (PublicWebCollectionDeniedError, PublicWebPolicyDeniedError) as exc:
            raise _execution_error(exc, "source_policy_denied", retryable=False) from exc
        except PublicWebParseError as exc:
            raise _execution_error(exc, "source_schema_drift", retryable=False) from exc
        except PublicWebResponseError as exc:
            raise _execution_error(exc, "unsafe_source_response", retryable=True) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise AdapterExecutionError(
                f"public web target returned HTTP {status}",
                error_code=f"http_{status}",
                retryable=status == 429 or status >= 500,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise _execution_error(exc, "source_transport_error", retryable=True) from exc
        return AdapterCollectionBatch(
            observations=batch.observations,
            checkpoint_payload=_checkpoint_payload(batch.checkpoint),
            not_modified=batch.not_modified,
            public_footprint_projections=batch.projections,
        )


def _checkpoint_from_payload(
    payload: Mapping[str, object] | None,
) -> PublicWebCheckpoint | None:
    if payload is None:
        return None
    raw_pages = payload.get("pages")
    if not isinstance(raw_pages, dict):
        raise AdapterExecutionError(
            "public web checkpoint pages must be a mapping",
            error_code="invalid_checkpoint",
            retryable=False,
        )
    pages: dict[str, PageCheckpoint] = {}
    for raw_url, raw_state in raw_pages.items():
        if not isinstance(raw_url, str) or not isinstance(raw_state, dict):
            raise AdapterExecutionError(
                "public web checkpoint page entries are invalid",
                error_code="invalid_checkpoint",
                retryable=False,
            )
        content_hash = raw_state.get("content_hash_sha256")
        version_id = raw_state.get("version_id")
        canonical_url = raw_state.get("canonical_url")
        resource_kind = raw_state.get("resource_kind", PublicResourceKind.WEB_PAGE.value)
        if (
            not isinstance(content_hash, str)
            or not isinstance(version_id, str)
            or not isinstance(canonical_url, str)
            or not isinstance(resource_kind, str)
        ):
            raise AdapterExecutionError(
                "public web checkpoint page state is invalid",
                error_code="invalid_checkpoint",
                retryable=False,
            )
        try:
            pages[raw_url] = PageCheckpoint(
                content_hash_sha256=content_hash,
                version_id=UUID(version_id),
                canonical_url=canonical_url,
                resource_kind=PublicResourceKind(resource_kind),
            )
        except ValueError as exc:
            raise AdapterExecutionError(
                "public web checkpoint page state is invalid",
                error_code="invalid_checkpoint",
                retryable=False,
            ) from exc
    return PublicWebCheckpoint(pages)


def _checkpoint_payload(checkpoint: PublicWebCheckpoint) -> dict[str, object]:
    return {
        "pages": {
            url: {
                "content_hash_sha256": state.content_hash_sha256,
                "version_id": str(state.version_id),
                "canonical_url": state.canonical_url,
                "resource_kind": state.resource_kind.value,
            }
            for url, state in sorted(checkpoint.pages.items())
        }
    }


def _execution_error(
    exc: Exception,
    error_code: str,
    *,
    retryable: bool,
) -> AdapterExecutionError:
    return AdapterExecutionError(
        str(exc) or type(exc).__name__,
        error_code=error_code,
        retryable=retryable,
    )

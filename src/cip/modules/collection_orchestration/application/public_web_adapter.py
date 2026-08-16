from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

import httpx

from cip.adapters.sources.public_web.checkpoint import (
    PublicWebCheckpointError,
    dump_checkpoint,
    load_checkpoint,
)
from cip.adapters.sources.public_web.client import (
    PublicWebClient,
    PublicWebDeadlineExceededError,
    PublicWebPolicyDeniedError,
    PublicWebResponseError,
)
from cip.adapters.sources.public_web.collection_policy import PublicWebCollectionDeniedError
from cip.adapters.sources.public_web.collector import collect_public_web_target
from cip.adapters.sources.public_web.crawl_runtime import CrawlDeadline, CrawlTelemetry
from cip.adapters.sources.public_web.parsing import PublicWebParseError
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
    AdapterOperationalMetrics,
    AdapterPartialExecutionError,
)
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
        if entry.policy.id != target.source_id:
            raise ValueError("public web adapter requires matching source identities")
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
        try:
            checkpoint = load_checkpoint(checkpoint_payload)
        except PublicWebCheckpointError as exc:
            raise _execution_error(exc, "invalid_checkpoint", retryable=False) from exc
        try:
            with httpx.Client(
                timeout=self._timeout_seconds,
                follow_redirects=False,
                transport=self._transport,
            ) as http_client:
                client = PublicWebClient(
                    http_client,
                    request_timeout_seconds=self._timeout_seconds,
                )
                client.bind_deadline(CrawlDeadline(self._target.crawl_deadline_seconds))
                batch = collect_public_web_target(
                    client,
                    self._entry,
                    self._target,
                    collection_job_id=collection_job_id,
                    collected_at=collected_at,
                    retention_until=retention_until,
                    checkpoint=checkpoint,
                )
        except PublicWebDeadlineExceededError as exc:
            raise _execution_error(exc, "crawl_deadline_exceeded", retryable=True) from exc
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

        adapter_batch = AdapterCollectionBatch(
            observations=batch.observations,
            checkpoint_payload=dump_checkpoint(batch.checkpoint),
            not_modified=batch.not_modified,
            public_footprint_projections=batch.projections,
            operational_metrics=_crawl_operational_metrics(batch.telemetry),
        )
        if batch.telemetry.deadline_exceeded:
            raise AdapterPartialExecutionError(
                "whole-crawl deadline exceeded after partial progress",
                error_code="crawl_deadline_exceeded",
                retryable=True,
                batch=adapter_batch,
            )
        return adapter_batch


def _crawl_operational_metrics(telemetry: CrawlTelemetry) -> AdapterOperationalMetrics:
    return AdapterOperationalMetrics(
        namespace="public_web.crawl.v1",
        values={
            "attempted_pages": telemetry.attempted_pages,
            "fetched_pages": telemetry.fetched_pages,
            "not_modified_pages": telemetry.not_modified_pages,
            "tombstoned_pages": telemetry.tombstoned_pages,
            "failed_pages": telemetry.failed_pages,
            "bytes_received": telemetry.bytes_received,
            "bytes_accepted": telemetry.bytes_accepted,
            "links_discovered": telemetry.links_discovered,
            "links_admitted": telemetry.links_admitted,
            "links_denied": telemetry.links_denied,
            "browser_fallback_count": telemetry.browser_fallback_count,
            "policy_denials": telemetry.policy_denials,
            "redirects": telemetry.redirects,
            "elapsed_seconds": telemetry.elapsed_seconds,
            "deadline_exceeded": telemetry.deadline_exceeded,
            "cancelled": telemetry.cancelled,
            "configured_concurrency": telemetry.configured_concurrency,
            "effective_concurrency": telemetry.effective_concurrency,
            "max_concurrency_used": telemetry.max_concurrency_used,
        },
    )


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

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

import httpx

from cip.adapters.sources.public_web.browser_client import BrowserPublicWebClient
from cip.adapters.sources.public_web.browser_runtime import BrowserRenderLimits
from cip.adapters.sources.public_web.checkpoint import (
    PublicWebCheckpointError,
    dump_checkpoint,
    load_checkpoint,
)
from cip.adapters.sources.public_web.client import (
    PublicWebPolicyDeniedError,
    PublicWebResponseError,
)
from cip.adapters.sources.public_web.collection_policy import PublicWebCollectionDeniedError
from cip.adapters.sources.public_web.collector import collect_public_web_target
from cip.adapters.sources.public_web.parsing import PublicWebParseError
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.source_governance.domain.models import DataCategory, SourceType
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


class PublicWebBrowserAdapter:
    adapter_id = "public-web-browser"
    data_category = DataCategory.OFFICIAL_DOCUMENT_DISCOVERY

    def __init__(
        self,
        entry: SourceRegistryEntry,
        target: PublicWebTarget,
        *,
        timeout_seconds: float = 30.0,
        browser_limits: BrowserRenderLimits | None = None,
    ) -> None:
        if entry.policy.id != target.source_id:
            raise ValueError("browser public web adapter requires matching source identities")
        if entry.policy.source_type is not SourceType.BROWSER:
            raise ValueError("browser public web adapter requires a browser source policy")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.source_id = target.id
        self._entry = entry
        self._target = target
        self._timeout_seconds = timeout_seconds
        self._browser_limits = browser_limits

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
            with httpx.Client(timeout=self._timeout_seconds, follow_redirects=False) as client:
                browser_client = BrowserPublicWebClient(
                    client,
                    self._entry,
                    collected_at=collected_at,
                    limits=self._browser_limits,
                )
                batch = collect_public_web_target(
                    browser_client,
                    self._entry,
                    self._target,
                    collection_job_id=collection_job_id,
                    collected_at=collected_at,
                    retention_until=retention_until,
                    checkpoint=checkpoint,
                    adapter_id=self.adapter_id,
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
                f"browser public web target returned HTTP {status}",
                error_code=f"http_{status}",
                retryable=status == 429 or status >= 500,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise _execution_error(exc, "source_transport_error", retryable=True) from exc
        return AdapterCollectionBatch(
            observations=batch.observations,
            checkpoint_payload=dump_checkpoint(batch.checkpoint),
            not_modified=batch.not_modified,
            public_footprint_projections=batch.projections,
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

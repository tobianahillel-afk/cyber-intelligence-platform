from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

import httpx

from cip.adapters.sources.public_web.browser_fallback import BrowserFallbackPolicy
from cip.adapters.sources.public_web.checkpoint import PublicWebCheckpointError, dump_checkpoint, load_checkpoint
from cip.adapters.sources.public_web.client import PublicWebPolicyDeniedError, PublicWebResponseError
from cip.adapters.sources.public_web.collection_policy import PublicWebCollectionDeniedError
from cip.adapters.sources.public_web.parsing import PublicWebParseError
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.ports import AdapterCollectionBatch, AdapterExecutionError
from cip.modules.collection_orchestration.application.public_web_fallback_collection import collect_with_browser_fallback
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


def execute_public_web_fallback(
    static_entry: SourceRegistryEntry,
    browser_entry: SourceRegistryEntry,
    target: PublicWebTarget,
    *,
    policy: BrowserFallbackPolicy,
    collection_job_id: UUID,
    checkpoint_payload: Mapping[str, object] | None,
    collected_at: datetime,
    retention_until: datetime,
    timeout_seconds: float,
    transport: httpx.BaseTransport | None,
    adapter_id: str,
) -> AdapterCollectionBatch:
    try:
        checkpoint = load_checkpoint(checkpoint_payload)
        batch = collect_with_browser_fallback(
            static_entry,
            browser_entry,
            target,
            policy=policy,
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
            checkpoint=checkpoint,
            timeout_seconds=timeout_seconds,
            transport=transport,
            adapter_id=adapter_id,
        )
    except PublicWebCheckpointError as exc:
        raise _error(exc, "invalid_checkpoint", False) from exc
    except (PublicWebCollectionDeniedError, PublicWebPolicyDeniedError) as exc:
        raise _error(exc, "source_policy_denied", False) from exc
    except PublicWebParseError as exc:
        raise _error(exc, "source_schema_drift", False) from exc
    except PublicWebResponseError as exc:
        raise _error(exc, "unsafe_source_response", True) from exc
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise AdapterExecutionError(
            f"public web fallback target returned HTTP {status}",
            error_code=f"http_{status}",
            retryable=status == 429 or status >= 500,
        ) from exc
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise _error(exc, "source_transport_error", True) from exc
    return AdapterCollectionBatch(
        observations=batch.observations,
        checkpoint_payload=dump_checkpoint(batch.checkpoint),
        not_modified=batch.not_modified,
        public_footprint_projections=batch.projections,
    )


def _error(exc: Exception, code: str, retryable: bool) -> AdapterExecutionError:
    return AdapterExecutionError(
        str(exc) or type(exc).__name__,
        error_code=code,
        retryable=retryable,
    )

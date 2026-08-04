from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

import httpx

from cip.adapters.sources.ted_search.client import (
    TedSearchCheckpoint,
    TedSearchClient,
    TedSourceResponseError,
)
from cip.adapters.sources.ted_search.collector import (
    TedCollectionDeniedError,
    TedSourceSchemaError,
    collect_ted_notices,
)
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


class TedSearchAdapter:
    source_id = "ted-search"
    adapter_id = "ted-search-api"
    data_category = DataCategory.PUBLIC_TENDER

    def __init__(self, entry: SourceRegistryEntry, *, timeout_seconds: float = 30.0) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("TED adapter requires the ted-search source policy")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._entry = entry
        self._timeout_seconds = timeout_seconds

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
            ) as http_client:
                batch = collect_ted_notices(
                    TedSearchClient(http_client, search_url=self._entry.policy.base_url),
                    self._entry,
                    collection_job_id=collection_job_id,
                    collected_at=collected_at,
                    retention_until=retention_until,
                    checkpoint=checkpoint,
                )
        except TedCollectionDeniedError as exc:
            raise _execution_error(exc, "source_policy_denied", retryable=False) from exc
        except TedSourceSchemaError as exc:
            raise _execution_error(exc, "source_schema_drift", retryable=False) from exc
        except TedSourceResponseError as exc:
            raise _execution_error(exc, "unsafe_source_response", retryable=True) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise AdapterExecutionError(
                f"TED Search returned HTTP {status}",
                error_code=f"http_{status}",
                retryable=status == 429 or status >= 500,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise _execution_error(exc, "source_transport_error", retryable=True) from exc
        return AdapterCollectionBatch(
            observations=batch.observations,
            checkpoint_payload={
                "latest_publication_number": batch.checkpoint.latest_publication_number,
            },
            not_modified=batch.not_modified,
            commercial_projections=batch.projections,
        )


def _checkpoint_from_payload(
    payload: Mapping[str, object] | None,
) -> TedSearchCheckpoint | None:
    if payload is None:
        return None
    value = payload.get("latest_publication_number")
    if value is not None and not isinstance(value, str):
        raise AdapterExecutionError(
            "checkpoint field latest_publication_number must be a string or null",
            error_code="invalid_checkpoint",
            retryable=False,
        )
    return TedSearchCheckpoint(latest_publication_number=value)


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

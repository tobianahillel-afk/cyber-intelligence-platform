from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

import httpx

from cip.adapters.sources.cordis_funding.client import (
    CordisFundingClient,
    CordisFundingResponseError,
)
from cip.adapters.sources.cordis_funding.collector import (
    CordisFundingCheckpoint,
    CordisFundingCollectionDeniedError,
    CordisFundingPaginationError,
    CordisFundingSchemaError,
    collect_cordis_funding,
)
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


class CordisFundingAdapter:
    source_id = "cordis-eu-funded-projects"
    adapter_id = "cordis-eurio-sparql-funding"
    data_category = DataCategory.PUBLIC_RESULT_METADATA

    def __init__(
        self,
        entry: SourceRegistryEntry,
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("CORDIS funding adapter requires its source policy")
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
            with httpx.Client(timeout=self._timeout_seconds, follow_redirects=False) as client:
                batch = collect_cordis_funding(
                    CordisFundingClient(client, endpoint_url=self._entry.policy.base_url),
                    self._entry,
                    collection_job_id=collection_job_id,
                    collected_at=collected_at,
                    retention_until=retention_until,
                    checkpoint=checkpoint,
                )
        except CordisFundingCollectionDeniedError as exc:
            raise _error(exc, "source_policy_denied", retryable=False) from exc
        except CordisFundingSchemaError as exc:
            raise _error(exc, "source_schema_drift", retryable=False) from exc
        except CordisFundingPaginationError as exc:
            raise _error(exc, "unsafe_pagination", retryable=False) from exc
        except CordisFundingResponseError as exc:
            raise _error(exc, "unsafe_source_response", retryable=True) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise AdapterExecutionError(
                f"CORDIS funding returned HTTP {status}",
                error_code=f"http_{status}",
                retryable=status == 429 or status >= 500,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise _error(exc, "source_transport_error", retryable=True) from exc
        checkpoint_payload_out: Mapping[str, object] | None = (
            {"offset": batch.checkpoint.offset} if batch.checkpoint else None
        )
        return AdapterCollectionBatch(
            observations=batch.observations,
            checkpoint_payload=checkpoint_payload_out,
            not_modified=batch.not_modified,
            corporate_change_claims=batch.claims,
        )


def _checkpoint_from_payload(
    payload: Mapping[str, object] | None,
) -> CordisFundingCheckpoint | None:
    if payload is None:
        return None
    value = payload.get("offset", 0)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise AdapterExecutionError(
            "CORDIS offset checkpoint must be a non-negative integer",
            error_code="invalid_checkpoint",
            retryable=False,
        )
    return CordisFundingCheckpoint(offset=value)


def _error(exc: Exception, error_code: str, *, retryable: bool) -> AdapterExecutionError:
    return AdapterExecutionError(
        str(exc) or type(exc).__name__,
        error_code=error_code,
        retryable=retryable,
    )

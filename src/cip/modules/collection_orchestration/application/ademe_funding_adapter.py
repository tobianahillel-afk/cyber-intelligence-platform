from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

import httpx

from cip.adapters.sources.ademe_funding.client import (
    AdemeFundingClient,
    AdemeFundingResponseError,
)
from cip.adapters.sources.ademe_funding.collector import (
    AdemeFundingCheckpoint,
    AdemeFundingCollectionDeniedError,
    AdemeFundingPaginationError,
    AdemeFundingSchemaError,
    collect_ademe_funding,
)
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


class AdemeFundingAdapter:
    source_id = "ademe-financial-aid"
    adapter_id = "ademe-data-fair-financial-aid-api"
    data_category = DataCategory.PUBLIC_RESULT_METADATA

    def __init__(
        self,
        entry: SourceRegistryEntry,
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("ADEME funding adapter requires its source policy")
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
                batch = collect_ademe_funding(
                    AdemeFundingClient(
                        http_client,
                        lines_url=self._entry.policy.base_url,
                    ),
                    self._entry,
                    collection_job_id=collection_job_id,
                    collected_at=collected_at,
                    retention_until=retention_until,
                    checkpoint=checkpoint,
                )
        except AdemeFundingCollectionDeniedError as exc:
            raise _execution_error(exc, "source_policy_denied", retryable=False) from exc
        except AdemeFundingSchemaError as exc:
            raise _execution_error(exc, "source_schema_drift", retryable=False) from exc
        except AdemeFundingPaginationError as exc:
            raise _execution_error(exc, "unsafe_pagination", retryable=False) from exc
        except AdemeFundingResponseError as exc:
            raise _execution_error(exc, "unsafe_source_response", retryable=True) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise AdapterExecutionError(
                f"ADEME funding returned HTTP {status}",
                error_code=f"http_{status}",
                retryable=status == 429 or status >= 500,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise _execution_error(exc, "source_transport_error", retryable=True) from exc
        return AdapterCollectionBatch(
            observations=batch.observations,
            checkpoint_payload={"next_url": batch.checkpoint.next_url},
            not_modified=batch.not_modified,
            corporate_change_claims=batch.claims,
        )


def _checkpoint_from_payload(
    payload: Mapping[str, object] | None,
) -> AdemeFundingCheckpoint | None:
    if payload is None:
        return None
    value = payload.get("next_url")
    if value is not None and not isinstance(value, str):
        raise AdapterExecutionError(
            "ADEME next_url checkpoint must be a string or null",
            error_code="invalid_checkpoint",
            retryable=False,
        )
    return AdemeFundingCheckpoint(next_url=value)


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

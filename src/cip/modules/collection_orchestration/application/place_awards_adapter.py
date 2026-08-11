from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

import httpx

from cip.adapters.sources.place_awards.client import (
    PlaceAwardsClient,
    PlaceSourceResponseError,
)
from cip.adapters.sources.place_awards.collector import (
    PlaceCheckpoint,
    PlaceCollectionDeniedError,
    PlaceSourceSchemaError,
    PlaceSourceWindowError,
    collect_place_awards,
)
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


class PlaceAwardsAdapter:
    source_id = "place-awards"
    adapter_id = "place-open-data-awards-api"
    data_category = DataCategory.CONTRACT_AWARD

    def __init__(
        self,
        entry: SourceRegistryEntry,
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("PLACE adapter requires its source policy")
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
                batch = collect_place_awards(
                    PlaceAwardsClient(
                        http_client,
                        records_url=self._entry.policy.base_url,
                    ),
                    self._entry,
                    collection_job_id=collection_job_id,
                    collected_at=collected_at,
                    retention_until=retention_until,
                    checkpoint=checkpoint,
                )
        except PlaceCollectionDeniedError as exc:
            raise _execution_error(exc, "source_policy_denied", retryable=False) from exc
        except PlaceSourceSchemaError as exc:
            raise _execution_error(exc, "source_schema_drift", retryable=False) from exc
        except PlaceSourceWindowError as exc:
            raise _execution_error(exc, "source_window_exceeded", retryable=False) from exc
        except PlaceSourceResponseError as exc:
            raise _execution_error(exc, "unsafe_source_response", retryable=True) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise AdapterExecutionError(
                f"PLACE returned HTTP {status}",
                error_code=f"http_{status}",
                retryable=status == 429 or status >= 500,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise _execution_error(exc, "source_transport_error", retryable=True) from exc
        return AdapterCollectionBatch(
            observations=batch.observations,
            checkpoint_payload={
                "latest_source_record_key": batch.checkpoint.latest_source_record_key,
                "latest_notification_date": batch.checkpoint.latest_notification_date,
            },
            not_modified=batch.not_modified,
            procurement_organizations=batch.buyers,
            procurement_projections=batch.procurement,
        )


def _checkpoint_from_payload(
    payload: Mapping[str, object] | None,
) -> PlaceCheckpoint | None:
    if payload is None:
        return None
    key = payload.get("latest_source_record_key")
    date_value = payload.get("latest_notification_date")
    if key is not None and not isinstance(key, str):
        raise _invalid_checkpoint()
    if date_value is not None and not isinstance(date_value, str):
        raise _invalid_checkpoint()
    return PlaceCheckpoint(key, date_value)


def _invalid_checkpoint() -> AdapterExecutionError:
    return AdapterExecutionError(
        "PLACE checkpoint fields must be strings or null",
        error_code="invalid_checkpoint",
        retryable=False,
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

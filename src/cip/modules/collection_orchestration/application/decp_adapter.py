from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

import httpx

from cip.adapters.sources.decp.client import (
    DecpCheckpoint,
    DecpClient,
    DecpSourceResponseError,
)
from cip.adapters.sources.decp.collector import (
    DecpCollectionDeniedError,
    DecpSourceSchemaError,
    DecpSourceWindowError,
    collect_decp_contracts,
)
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


class DecpAdapter:
    source_id = "decp"
    adapter_id = "decp-explore-api"
    data_category = DataCategory.PUBLIC_TENDER

    def __init__(self, entry: SourceRegistryEntry, *, timeout_seconds: float = 30.0) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("DECP adapter requires the decp source policy")
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
                batch = collect_decp_contracts(
                    DecpClient(http_client, records_url=self._entry.policy.base_url),
                    self._entry,
                    collection_job_id=collection_job_id,
                    collected_at=collected_at,
                    retention_until=retention_until,
                    checkpoint=checkpoint,
                )
        except DecpCollectionDeniedError as exc:
            raise _execution_error(exc, "source_policy_denied", retryable=False) from exc
        except DecpSourceSchemaError as exc:
            raise _execution_error(exc, "source_schema_drift", retryable=False) from exc
        except DecpSourceWindowError as exc:
            raise _execution_error(exc, "source_window_exceeded", retryable=False) from exc
        except DecpSourceResponseError as exc:
            raise _execution_error(exc, "unsafe_source_response", retryable=True) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise AdapterExecutionError(
                f"DECP returned HTTP {status}",
                error_code=f"http_{status}",
                retryable=status == 429 or status >= 500,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise _execution_error(exc, "source_transport_error", retryable=True) from exc
        return AdapterCollectionBatch(
            observations=batch.observations,
            checkpoint_payload={
                "latest_revision_key": batch.checkpoint.latest_revision_key,
                "latest_publication_date": batch.checkpoint.latest_publication_date,
            },
            not_modified=batch.not_modified,
            procurement_organizations=batch.buyers,
            procurement_projections=batch.procurement,
        )


def _checkpoint_from_payload(
    payload: Mapping[str, object] | None,
) -> DecpCheckpoint | None:
    if payload is None:
        return None
    return DecpCheckpoint(
        latest_revision_key=_optional_string(payload, "latest_revision_key"),
        latest_publication_date=_optional_string(payload, "latest_publication_date"),
    )


def _optional_string(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise AdapterExecutionError(
            f"checkpoint field {key} must be a string or null",
            error_code="invalid_checkpoint",
            retryable=False,
        )
    return value


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

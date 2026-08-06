from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

import httpx

from cip.adapters.sources.cisa_kev.client import (
    CisaKevCheckpoint,
    CisaKevClient,
    SourceResponseError,
)
from cip.adapters.sources.cisa_kev.collector import (
    CollectionDeniedError,
    SourceSchemaError,
    collect_cisa_kev,
)
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


class CisaKevAdapter:
    source_id = "cisa-kev"
    adapter_id = "cisa-kev-feed"
    data_category = DataCategory.VULNERABILITY_METADATA

    def __init__(self, entry: SourceRegistryEntry, *, timeout_seconds: float = 30.0) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("CISA adapter requires the cisa-kev source policy")
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
                batch = collect_cisa_kev(
                    CisaKevClient(http_client, feed_url=self._entry.policy.base_url),
                    self._entry,
                    collection_job_id=collection_job_id,
                    collected_at=collected_at,
                    retention_until=retention_until,
                    checkpoint=checkpoint,
                )
        except CollectionDeniedError as exc:
            raise AdapterExecutionError(
                str(exc),
                error_code="source_policy_denied",
                retryable=False,
            ) from exc
        except SourceSchemaError as exc:
            raise AdapterExecutionError(
                str(exc),
                error_code="source_schema_drift",
                retryable=False,
            ) from exc
        except SourceResponseError as exc:
            raise AdapterExecutionError(
                str(exc),
                error_code="unsafe_source_response",
                retryable=True,
            ) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise AdapterExecutionError(
                f"CISA KEV returned HTTP {status}",
                error_code=f"http_{status}",
                retryable=status == 429 or status >= 500,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise AdapterExecutionError(
                str(exc) or type(exc).__name__,
                error_code="source_transport_error",
                retryable=True,
            ) from exc

        return AdapterCollectionBatch(
            observations=batch.observations,
            checkpoint_payload={
                "etag": batch.checkpoint.etag,
                "last_modified": batch.checkpoint.last_modified,
                "catalog_version": batch.checkpoint.catalog_version,
            },
            not_modified=batch.not_modified,
            vulnerability_snapshots=batch.vulnerability_snapshots,
        )


def _checkpoint_from_payload(
    payload: Mapping[str, object] | None,
) -> CisaKevCheckpoint | None:
    if payload is None:
        return None
    return CisaKevCheckpoint(
        etag=_optional_string(payload, "etag"),
        last_modified=_optional_string(payload, "last_modified"),
        catalog_version=_optional_string(payload, "catalog_version"),
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

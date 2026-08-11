from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import TypeGuard
from uuid import UUID

import httpx

from cip.adapters.sources.cordis_funding.client import (
    CordisFundingClient,
    CordisFundingResponseError,
)
from cip.adapters.sources.cordis_funding.collector import (
    CordisFundingArchiveError,
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
    adapter_id = "cordis-horizon-bulk-csv"
    data_category = DataCategory.PUBLIC_RESULT_METADATA

    def __init__(
        self,
        entry: SourceRegistryEntry,
        *,
        timeout_seconds: float = 120.0,
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
                    CordisFundingClient(client, archive_url=self._entry.policy.base_url),
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
        except (CordisFundingArchiveError, CordisFundingPaginationError) as exc:
            raise _error(exc, "unsafe_source_archive", retryable=False) from exc
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
        checkpoint_payload_out: Mapping[str, object] = {
            "archive_sha256": batch.checkpoint.archive_sha256,
            "offset": batch.checkpoint.offset,
            "complete": batch.checkpoint.complete,
        }
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
    archive_hash = payload.get("archive_sha256")
    offset = payload.get("offset", 0)
    complete = payload.get("complete", False)
    if not _valid_hash(archive_hash):
        raise _checkpoint_error("CORDIS archive hash checkpoint is invalid")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise _checkpoint_error("CORDIS offset checkpoint must be a non-negative integer")
    if not isinstance(complete, bool):
        raise _checkpoint_error("CORDIS complete checkpoint must be boolean")
    return CordisFundingCheckpoint(
        archive_sha256=archive_hash,
        offset=offset,
        complete=complete,
    )


def _valid_hash(value: object) -> TypeGuard[str]:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(character in "0123456789abcdef" for character in value)


def _checkpoint_error(message: str) -> AdapterExecutionError:
    return AdapterExecutionError(message, error_code="invalid_checkpoint", retryable=False)


def _error(exc: Exception, error_code: str, *, retryable: bool) -> AdapterExecutionError:
    return AdapterExecutionError(
        str(exc) or type(exc).__name__,
        error_code=error_code,
        retryable=retryable,
    )

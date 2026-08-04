from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

import httpx

from cip.adapters.sources.lever.client import LeverClient, LeverSourceResponseError
from cip.adapters.sources.lever.collector import (
    LeverCheckpoint,
    LeverCollectionDeniedError,
    LeverSourceSchemaError,
    LeverSourceWindowError,
    collect_lever_jobs,
)
from cip.adapters.sources.lever.registry import LeverSite
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


class LeverAdapter:
    source_id = "lever-job-board"
    adapter_id = "lever-postings-api"
    data_category = DataCategory.PUBLIC_JOB_POSTING

    def __init__(
        self,
        entry: SourceRegistryEntry,
        sites: tuple[LeverSite, ...],
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("Lever adapter requires its source policy")
        if not any(site.enabled for site in sites):
            raise ValueError("Lever adapter requires an enabled site")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._entry = entry
        self._sites = sites
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
                batch = collect_lever_jobs(
                    LeverClient(
                        http_client,
                        postings_base_url=self._entry.policy.base_url,
                    ),
                    self._entry,
                    self._sites,
                    collection_job_id=collection_job_id,
                    collected_at=collected_at,
                    retention_until=retention_until,
                    checkpoint=checkpoint,
                )
        except LeverCollectionDeniedError as exc:
            raise _execution_error(exc, "source_policy_denied", retryable=False) from exc
        except LeverSourceSchemaError as exc:
            raise _execution_error(exc, "source_schema_drift", retryable=False) from exc
        except LeverSourceWindowError as exc:
            raise _execution_error(exc, "source_window_exceeded", retryable=False) from exc
        except LeverSourceResponseError as exc:
            raise _execution_error(exc, "unsafe_source_response", retryable=True) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise AdapterExecutionError(
                f"Lever returned HTTP {status}",
                error_code=f"http_{status}",
                retryable=status == 429 or status >= 500,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise _execution_error(exc, "source_transport_error", retryable=True) from exc
        return AdapterCollectionBatch(
            observations=batch.observations,
            checkpoint_payload={
                "fingerprints": {
                    site_id: dict(values)
                    for site_id, values in batch.checkpoint.fingerprints.items()
                }
            },
            not_modified=batch.not_modified,
            commercial_projections=batch.projections,
        )


def _checkpoint_from_payload(
    payload: Mapping[str, object] | None,
) -> LeverCheckpoint | None:
    if payload is None:
        return None
    raw_fingerprints = payload.get("fingerprints")
    if not isinstance(raw_fingerprints, dict):
        raise AdapterExecutionError(
            "checkpoint fingerprints must be a mapping",
            error_code="invalid_checkpoint",
            retryable=False,
        )
    fingerprints: dict[str, dict[str, str]] = {}
    for site_id, raw_jobs in raw_fingerprints.items():
        if not isinstance(site_id, str) or not isinstance(raw_jobs, dict):
            raise _invalid_checkpoint()
        jobs: dict[str, str] = {}
        for job_id, fingerprint in raw_jobs.items():
            if not isinstance(job_id, str) or not isinstance(fingerprint, str):
                raise _invalid_checkpoint()
            jobs[job_id] = fingerprint
        fingerprints[site_id] = jobs
    return LeverCheckpoint(fingerprints)


def _invalid_checkpoint() -> AdapterExecutionError:
    return AdapterExecutionError(
        "checkpoint fingerprints must contain string site, job, and hash values",
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

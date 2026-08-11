from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from uuid import UUID

import httpx

from cip.adapters.sources.teamtailor.client import (
    TeamtailorClient,
    TeamtailorSourceResponseError,
)
from cip.adapters.sources.teamtailor.collector import (
    TeamtailorCheckpoint,
    TeamtailorCollectionDeniedError,
    TeamtailorSourceSchemaError,
    TeamtailorSourceWindowError,
    collect_teamtailor_jobs,
)
from cip.adapters.sources.teamtailor.registry import TeamtailorAccount
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


class TeamtailorAdapter:
    source_id = "teamtailor-public-jobs"
    adapter_id = "teamtailor-public-read-jobs-api"
    data_category = DataCategory.PUBLIC_JOB_POSTING

    def __init__(
        self,
        entry: SourceRegistryEntry,
        account: TeamtailorAccount,
        token_provider: Callable[[], str | None],
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("Teamtailor adapter requires its source policy")
        if not account.enabled:
            raise ValueError("Teamtailor adapter requires an enabled account")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._entry = entry
        self._account = account
        self._token_provider = token_provider
        self._timeout_seconds = timeout_seconds

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch:
        token = self._token_provider()
        if token is None or not token.strip():
            raise AdapterExecutionError(
                "Teamtailor Public Read API token is unavailable",
                error_code="provider_secret_unavailable",
                retryable=False,
            )
        checkpoint = _checkpoint_from_payload(checkpoint_payload)
        try:
            with httpx.Client(
                timeout=self._timeout_seconds,
                follow_redirects=False,
            ) as http_client:
                batch = collect_teamtailor_jobs(
                    TeamtailorClient(http_client),
                    self._entry,
                    self._account,
                    api_token=token,
                    collection_job_id=collection_job_id,
                    collected_at=collected_at,
                    retention_until=retention_until,
                    checkpoint=checkpoint,
                )
        except TeamtailorCollectionDeniedError as exc:
            raise _execution_error(exc, "source_policy_denied", retryable=False) from exc
        except TeamtailorSourceSchemaError as exc:
            raise _execution_error(exc, "source_schema_drift", retryable=False) from exc
        except TeamtailorSourceWindowError as exc:
            raise _execution_error(exc, "source_window_exceeded", retryable=False) from exc
        except TeamtailorSourceResponseError as exc:
            raise _execution_error(exc, "unsafe_source_response", retryable=True) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise AdapterExecutionError(
                f"Teamtailor returned HTTP {status}",
                error_code=f"http_{status}",
                retryable=status == 429 or status >= 500,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise _execution_error(exc, "source_transport_error", retryable=True) from exc
        return AdapterCollectionBatch(
            observations=batch.observations,
            checkpoint_payload={
                "fingerprints": {
                    account_id: dict(values)
                    for account_id, values in batch.checkpoint.fingerprints.items()
                }
            },
            not_modified=batch.not_modified,
            commercial_projections=batch.projections,
        )


def _checkpoint_from_payload(
    payload: Mapping[str, object] | None,
) -> TeamtailorCheckpoint | None:
    if payload is None:
        return None
    raw_fingerprints = payload.get("fingerprints")
    if not isinstance(raw_fingerprints, dict):
        raise _invalid_checkpoint()
    fingerprints: dict[str, dict[str, str]] = {}
    for account_id, raw_jobs in raw_fingerprints.items():
        if not isinstance(account_id, str) or not isinstance(raw_jobs, dict):
            raise _invalid_checkpoint()
        jobs: dict[str, str] = {}
        for job_id, fingerprint in raw_jobs.items():
            if not isinstance(job_id, str) or not isinstance(fingerprint, str):
                raise _invalid_checkpoint()
            jobs[job_id] = fingerprint
        fingerprints[account_id] = jobs
    return TeamtailorCheckpoint(fingerprints)


def _invalid_checkpoint() -> AdapterExecutionError:
    return AdapterExecutionError(
        "checkpoint fingerprints must contain string account, job, and hash values",
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

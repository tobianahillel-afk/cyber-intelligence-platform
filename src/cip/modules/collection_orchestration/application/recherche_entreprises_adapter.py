from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

import httpx

from cip.adapters.sources.organization_identity.registry import OrganizationIdentityTarget
from cip.adapters.sources.recherche_entreprises.client import (
    RechercheEntreprisesClient,
    RechercheEntreprisesSourceResponseError,
)
from cip.adapters.sources.recherche_entreprises.collector import (
    RechercheEntreprisesCheckpoint,
    RechercheEntreprisesCollectionDeniedError,
    RechercheEntreprisesSourceSchemaError,
    RechercheEntreprisesSourceWindowError,
    collect_recherche_entreprises,
)
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


class RechercheEntreprisesAdapter:
    source_id = "recherche-entreprises"
    adapter_id = "recherche-entreprises-search"
    data_category = DataCategory.ORGANIZATION_METADATA

    def __init__(
        self,
        entry: SourceRegistryEntry,
        targets: tuple[OrganizationIdentityTarget, ...],
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("Recherche d'entreprises adapter requires its source policy")
        if not any(target.enabled and target.country_code == "FR" for target in targets):
            raise ValueError("Recherche d'entreprises adapter requires an enabled French target")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._entry = entry
        self._targets = targets
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
                batch = collect_recherche_entreprises(
                    RechercheEntreprisesClient(
                        http_client,
                        search_url=self._entry.policy.base_url,
                    ),
                    self._entry,
                    self._targets,
                    collection_job_id=collection_job_id,
                    collected_at=collected_at,
                    retention_until=retention_until,
                    checkpoint=checkpoint,
                )
        except RechercheEntreprisesCollectionDeniedError as exc:
            raise _execution_error(exc, "source_policy_denied", retryable=False) from exc
        except RechercheEntreprisesSourceSchemaError as exc:
            raise _execution_error(exc, "source_schema_drift", retryable=False) from exc
        except RechercheEntreprisesSourceWindowError as exc:
            raise _execution_error(exc, "source_window_exceeded", retryable=False) from exc
        except RechercheEntreprisesSourceResponseError as exc:
            raise _execution_error(exc, "unsafe_source_response", retryable=True) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise AdapterExecutionError(
                f"Recherche d'entreprises returned HTTP {status}",
                error_code=f"http_{status}",
                retryable=status == 429 or status >= 500,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise _execution_error(exc, "source_transport_error", retryable=True) from exc
        return AdapterCollectionBatch(
            observations=batch.observations,
            checkpoint_payload={
                "fingerprints": {
                    target_id: dict(values)
                    for target_id, values in batch.checkpoint.fingerprints.items()
                }
            },
            not_modified=batch.not_modified,
            identity_projections=batch.projections,
        )


def _checkpoint_from_payload(
    payload: Mapping[str, object] | None,
) -> RechercheEntreprisesCheckpoint | None:
    if payload is None:
        return None
    raw_fingerprints = payload.get("fingerprints")
    if not isinstance(raw_fingerprints, dict):
        raise _invalid_checkpoint()
    fingerprints: dict[str, dict[str, str]] = {}
    for target_id, raw_records in raw_fingerprints.items():
        if not isinstance(target_id, str) or not isinstance(raw_records, dict):
            raise _invalid_checkpoint()
        records: dict[str, str] = {}
        for record_id, fingerprint in raw_records.items():
            if not isinstance(record_id, str) or not isinstance(fingerprint, str):
                raise _invalid_checkpoint()
            records[record_id] = fingerprint
        fingerprints[target_id] = records
    return RechercheEntreprisesCheckpoint(fingerprints)


def _invalid_checkpoint() -> AdapterExecutionError:
    return AdapterExecutionError(
        "checkpoint fingerprints must contain string target, record, and hash values",
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

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

import httpx

from cip.adapters.sources.bodacc_identity.client import (
    BodaccIdentityClient,
    BodaccIdentitySourceResponseError,
)
from cip.adapters.sources.bodacc_identity.collector import (
    BodaccIdentityCheckpoint,
    BodaccIdentityCollectionDeniedError,
    BodaccIdentitySourceSchemaError,
    BodaccIdentitySourceWindowError,
    collect_bodacc_identities,
)
from cip.adapters.sources.organization_identity.registry import OrganizationIdentityTarget
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


class BodaccIdentityAdapter:
    source_id = "bodacc-identity"
    adapter_id = "bodacc-commercial-announcements"
    data_category = DataCategory.ORGANIZATION_METADATA

    def __init__(
        self,
        entry: SourceRegistryEntry,
        targets: tuple[OrganizationIdentityTarget, ...],
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("BODACC identity adapter requires its source policy")
        if not any(
            target.enabled and target.country_code == "FR" and target.siren
            for target in targets
        ):
            raise ValueError("BODACC identity adapter requires an enabled French SIREN target")
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
                batch = collect_bodacc_identities(
                    BodaccIdentityClient(
                        http_client,
                        records_url=self._entry.policy.base_url,
                    ),
                    self._entry,
                    self._targets,
                    collection_job_id=collection_job_id,
                    collected_at=collected_at,
                    retention_until=retention_until,
                    checkpoint=checkpoint,
                )
        except BodaccIdentityCollectionDeniedError as exc:
            raise _execution_error(exc, "source_policy_denied", retryable=False) from exc
        except BodaccIdentitySourceSchemaError as exc:
            raise _execution_error(exc, "source_schema_drift", retryable=False) from exc
        except BodaccIdentitySourceWindowError as exc:
            raise _execution_error(exc, "source_window_exceeded", retryable=False) from exc
        except BodaccIdentitySourceResponseError as exc:
            raise _execution_error(exc, "unsafe_source_response", retryable=True) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise AdapterExecutionError(
                f"BODACC returned HTTP {status}",
                error_code=f"http_{status}",
                retryable=status == 429 or status >= 500,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise _execution_error(exc, "source_transport_error", retryable=True) from exc
        return AdapterCollectionBatch(
            observations=batch.observations,
            checkpoint_payload={"fingerprints": dict(batch.checkpoint.fingerprints)},
            not_modified=batch.not_modified,
            identity_projections=batch.projections,
        )


def _checkpoint_from_payload(
    payload: Mapping[str, object] | None,
) -> BodaccIdentityCheckpoint | None:
    if payload is None:
        return None
    raw_fingerprints = payload.get("fingerprints")
    if not isinstance(raw_fingerprints, dict):
        raise _invalid_checkpoint()
    fingerprints: dict[str, str] = {}
    for target_id, fingerprint in raw_fingerprints.items():
        if not isinstance(target_id, str) or not isinstance(fingerprint, str):
            raise _invalid_checkpoint()
        fingerprints[target_id] = fingerprint
    return BodaccIdentityCheckpoint(fingerprints)


def _invalid_checkpoint() -> AdapterExecutionError:
    return AdapterExecutionError(
        "checkpoint fingerprints must contain string target and hash values",
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

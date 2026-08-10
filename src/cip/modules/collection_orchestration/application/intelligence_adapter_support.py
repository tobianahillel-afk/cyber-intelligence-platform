from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from uuid import UUID

import httpx
from pydantic import BaseModel

from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    SourceRuntimeState,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

DEFAULT_MAX_JSON_BYTES = 8 * 1024 * 1024
HARD_MAX_JSON_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class IntelligenceObservationContext:
    source_id: str
    adapter_id: str
    adapter_version: str
    collection_job_id: UUID
    data_category: DataCategory
    collected_at: datetime
    retention_until: datetime


def authorize_intelligence_request(
    entry: SourceRegistryEntry,
    *,
    category: DataCategory,
    purpose: str,
    target_url: str,
    collected_at: datetime,
) -> None:
    decision = entry.policy.evaluate(
        CollectionRequest(
            data_category=category,
            target_url=target_url,
            purpose=purpose,
            automated=True,
            store_raw_content=False,
            human_review_completed=True,
        ),
        entry.authorization,
        SourceRuntimeState(remaining_requests=1),
        now=collected_at,
    )
    if not decision.allowed:
        raise AdapterExecutionError(
            decision.reason.value,
            error_code="source_policy_denied",
            retryable=False,
        )


def get_json(
    client: httpx.Client,
    target_url: str,
    *,
    headers: Mapping[str, str],
    params: Mapping[str, str | int] | None = None,
    max_bytes: int = DEFAULT_MAX_JSON_BYTES,
) -> bytes:
    if not 1 <= max_bytes <= HARD_MAX_JSON_BYTES:
        raise ValueError("max_bytes is outside the intelligence response bound")
    try:
        response = client.get(target_url, headers=headers, params=params)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise AdapterExecutionError(
            f"intelligence provider returned HTTP {status}",
            error_code=f"http_{status}",
            retryable=status == 429 or status >= 500,
        ) from exc
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise AdapterExecutionError(
            "intelligence provider transport failure",
            error_code="source_transport_error",
            retryable=True,
        ) from exc
    if "json" not in response.headers.get("content-type", "").casefold():
        raise AdapterExecutionError(
            "intelligence provider response is not JSON",
            error_code="unsafe_source_response",
            retryable=False,
        )
    if len(response.content) > max_bytes:
        raise AdapterExecutionError(
            "intelligence provider response exceeds size limit",
            error_code="unsafe_source_response",
            retryable=False,
        )
    return response.content


def raw_intelligence_observation(
    model: BaseModel,
    *,
    context: IntelligenceObservationContext,
    source_url: str,
    source_record_key: str,
    source_record_type: str,
    observed_at: datetime | None = None,
    published_at: datetime | None = None,
    source_updated_at: datetime | None = None,
) -> RawObservation:
    encoded = model.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")
    return RawObservation(
        source_id=context.source_id,
        adapter_id=context.adapter_id,
        adapter_version=context.adapter_version,
        collection_job_id=context.collection_job_id,
        source_record_type=source_record_type,
        source_url=source_url,
        payload_hash_sha256=sha256(encoded).hexdigest(),
        data_categories=frozenset({context.data_category}),
        source_record_key=source_record_key,
        collected_at=context.collected_at,
        observed_at=observed_at,
        published_at=published_at,
        source_updated_at=source_updated_at,
        retention_until=context.retention_until,
        schema_fingerprint=f"{source_record_type}:v1",
    )

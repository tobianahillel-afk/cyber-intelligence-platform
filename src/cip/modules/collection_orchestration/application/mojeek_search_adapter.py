from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from hashlib import sha256
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from pydantic import ValidationError

from cip.adapters.sources.mojeek_search.registry import MojeekSearchEntitlement
from cip.adapters.sources.mojeek_search.schemas import MojeekSearchResponse, MojeekWebResult
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.public_footprint.domain.search import (
    SearchQueryTemplate,
    SearchResultLead,
    map_search_result_lead,
)
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    SourceRuntimeState,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_MAX_RESULTS = 20


class MojeekSearchAdapter:
    source_id = "mojeek-web-search-metadata"
    adapter_id = "mojeek-web-search"
    adapter_version = "1"
    data_category = DataCategory.PUBLIC_RESULT_METADATA

    def __init__(
        self,
        entry: SourceRegistryEntry,
        targets: tuple[PublicWebTarget, ...],
        templates: tuple[SearchQueryTemplate, ...],
        entitlement: MojeekSearchEntitlement,
        *,
        token_provider: Callable[[], str | None],
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("Mojeek adapter requires mojeek-web-search-metadata policy")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._entry = entry
        self._pairs = tuple(
            (target, template)
            for target in targets
            if target.enabled
            for template in templates
            if template.enabled
        )
        self._entitlement = entitlement
        self._token_provider = token_provider
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch:
        pair, next_index = _next_pair(self._pairs, checkpoint_payload)
        if pair is None:
            return _empty_batch()
        target, template = pair
        query = template.render(target.canonical_name)
        target_url = self._entry.policy.base_url
        _authorize(self._entry, target_url, template.purpose, collected_at)
        if not self._entitlement.durable_storage_authorized:
            raise AdapterExecutionError(
                "Mojeek durable result storage entitlement is not authorized",
                error_code="provider_storage_entitlement_missing",
                retryable=False,
            )
        api_key = self._token_provider()
        if api_key is None or not api_key.strip():
            raise AdapterExecutionError(
                "Mojeek provider secret is unavailable",
                error_code="provider_not_connected",
                retryable=False,
            )
        response = _request(
            target_url,
            query=query,
            api_key=api_key.strip(),
            timeout_seconds=self._timeout_seconds,
            transport=self._transport,
        )
        try:
            parsed = MojeekSearchResponse.model_validate_json(response)
        except ValidationError as exc:
            raise AdapterExecutionError(
                "Mojeek response schema changed",
                error_code="source_schema_drift",
                retryable=False,
            ) from exc
        if parsed.response.status.casefold() != "ok":
            raise AdapterExecutionError(
                "Mojeek provider returned a non-OK response status",
                error_code="provider_response_error",
                retryable=False,
            )
        results = tuple(
            result for result in parsed.response.results[:_MAX_RESULTS] if _safe_result(result)
        )
        observations = tuple(
            _observation(
                result,
                target=target,
                template=template,
                collection_job_id=collection_job_id,
                collected_at=collected_at,
                retention_until=retention_until,
                source_url=target_url,
            )
            for result in results
        )
        projections = tuple(
            map_search_result_lead(
                SearchResultLead(
                    organization_id=target.organization_id,
                    source_id=self.source_id,
                    source_record_key=_record_key(query, result.url),
                    target_url=result.url,
                    title=result.title,
                    snippet=result.desc[:1_000],
                    rank=rank,
                    observed_at=collected_at,
                    query_template_id=template.id,
                    query_template_version=template.version,
                )
            )
            for rank, result in enumerate(results, start=1)
        )
        return AdapterCollectionBatch(
            observations=observations,
            public_footprint_projections=projections,
            checkpoint_payload={"pair_index": next_index},
            not_modified=not results,
        )


def _authorize(
    entry: SourceRegistryEntry,
    target_url: str,
    purpose: str,
    now: datetime,
) -> None:
    decision = entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.PUBLIC_RESULT_METADATA,
            target_url=target_url,
            purpose=purpose,
            automated=True,
            store_raw_content=False,
            human_review_completed=True,
        ),
        entry.authorization,
        SourceRuntimeState(remaining_requests=1),
        now=now,
    )
    if not decision.allowed:
        raise AdapterExecutionError(
            decision.reason.value,
            error_code="source_policy_denied",
            retryable=False,
        )


def _request(
    target_url: str,
    *,
    query: str,
    api_key: str,
    timeout_seconds: float,
    transport: httpx.BaseTransport | None,
) -> bytes:
    try:
        with httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=False,
            transport=transport,
        ) as client:
            response = client.get(
                target_url,
                headers={"Accept": "application/json"},
                params={
                    "api_key": api_key,
                    "q": query,
                    "t": _MAX_RESULTS,
                    "fmt": "json",
                },
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise AdapterExecutionError(
            f"Mojeek Search returned HTTP {status}",
            error_code=f"http_{status}",
            retryable=status == 429 or status >= 500,
        ) from exc
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise AdapterExecutionError(
            str(exc) or type(exc).__name__,
            error_code="source_transport_error",
            retryable=True,
        ) from exc
    if "json" not in response.headers.get("content-type", "").casefold():
        raise AdapterExecutionError(
            "Mojeek Search response is not JSON",
            error_code="unsafe_source_response",
            retryable=False,
        )
    if len(response.content) > _MAX_RESPONSE_BYTES:
        raise AdapterExecutionError(
            "Mojeek Search response exceeds size limit",
            error_code="unsafe_source_response",
            retryable=False,
        )
    return response.content


def _safe_result(result: MojeekWebResult) -> bool:
    parsed = urlsplit(result.url)
    return parsed.scheme in {"http", "https"} and parsed.hostname is not None


def _observation(
    result: MojeekWebResult,
    *,
    target: PublicWebTarget,
    template: SearchQueryTemplate,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    source_url: str,
) -> RawObservation:
    payload = result.model_dump_json(exclude_none=True).encode("utf-8")
    query = template.render(target.canonical_name)
    return RawObservation(
        source_id=MojeekSearchAdapter.source_id,
        adapter_id=MojeekSearchAdapter.adapter_id,
        adapter_version=MojeekSearchAdapter.adapter_version,
        collection_job_id=collection_job_id,
        source_record_type="mojeek-search-result",
        source_url=source_url,
        payload_hash_sha256=sha256(payload).hexdigest(),
        data_categories=frozenset({DataCategory.PUBLIC_RESULT_METADATA}),
        source_record_key=_record_key(query, result.url),
        collected_at=collected_at,
        retention_until=retention_until,
        schema_fingerprint="mojeek-web-search:v1",
    )


def _record_key(query: str, result_url: str) -> str:
    return sha256(f"{query}\0{result_url}".encode()).hexdigest()


def _next_pair(
    pairs: tuple[tuple[PublicWebTarget, SearchQueryTemplate], ...],
    payload: Mapping[str, object] | None,
) -> tuple[tuple[PublicWebTarget, SearchQueryTemplate] | None, int]:
    if not pairs:
        return None, 0
    value = 0 if payload is None else payload.get("pair_index", 0)
    if not isinstance(value, int) or value < 0:
        raise AdapterExecutionError(
            "invalid Mojeek Search checkpoint",
            error_code="invalid_checkpoint",
            retryable=False,
        )
    index = value % len(pairs)
    return pairs[index], 0 if index + 1 >= len(pairs) else index + 1


def _empty_batch() -> AdapterCollectionBatch:
    return AdapterCollectionBatch(
        observations=(),
        public_footprint_projections=(),
        checkpoint_payload={"pair_index": 0},
        not_modified=True,
    )

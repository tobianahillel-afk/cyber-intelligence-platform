from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from hashlib import sha256
from urllib.parse import urlsplit
from uuid import UUID

import httpx

from cip.adapters.sources.marginalia_search.client import (
    MarginaliaSearchClient,
    MarginaliaSearchClientError,
)
from cip.adapters.sources.marginalia_search.registry import MarginaliaSearchEntitlement
from cip.adapters.sources.marginalia_search.schemas import MarginaliaSearchResult
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

_MAX_RESULTS = 20


class MarginaliaSearchAdapter:
    source_id = "marginalia-web-search-metadata"
    adapter_id = "marginalia-search-api2"
    adapter_version = "1"
    data_category = DataCategory.PUBLIC_RESULT_METADATA

    def __init__(
        self,
        entry: SourceRegistryEntry,
        targets: tuple[PublicWebTarget, ...],
        templates: tuple[SearchQueryTemplate, ...],
        entitlement: MarginaliaSearchEntitlement,
        *,
        token_provider: Callable[[], str | None],
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("Marginalia adapter requires marginalia-web-search-metadata policy")
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
        try:
            self._entitlement.assert_live_collection_ready()
        except PermissionError as exc:
            raise AdapterExecutionError(
                str(exc),
                error_code="provider_commercial_entitlement_missing",
                retryable=False,
            ) from exc
        api_key = self._token_provider()
        if api_key is None or not api_key.strip():
            raise AdapterExecutionError(
                "Marginalia provider secret is unavailable",
                error_code="provider_not_connected",
                retryable=False,
            )
        try:
            result = MarginaliaSearchClient(
                self._entitlement,
                timeout_seconds=self._timeout_seconds,
                transport=self._transport,
            ).search(query=query, api_key=api_key.strip())
        except MarginaliaSearchClientError as exc:
            raise AdapterExecutionError(
                str(exc),
                error_code=exc.code,
                retryable=exc.retryable,
            ) from exc
        except PermissionError as exc:
            raise AdapterExecutionError(
                str(exc),
                error_code="provider_credential_rejected",
                retryable=False,
            ) from exc

        results = tuple(
            item for item in result.response.results[:_MAX_RESULTS] if _safe_result(item)
        )
        observations = tuple(
            _observation(
                item,
                target=target,
                template=template,
                collection_job_id=collection_job_id,
                collected_at=collected_at,
                retention_until=retention_until,
                source_url=target_url,
            )
            for item in results
        )
        projections = tuple(
            map_search_result_lead(
                SearchResultLead(
                    organization_id=target.organization_id,
                    source_id=self.source_id,
                    source_record_key=_record_key(query, item.url),
                    target_url=item.url,
                    title=item.title,
                    snippet=item.description[:1_000],
                    rank=rank,
                    observed_at=collected_at,
                    query_template_id=template.id,
                    query_template_version=template.version,
                )
            )
            for rank, item in enumerate(results, start=1)
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


def _safe_result(result: MarginaliaSearchResult) -> bool:
    parsed = urlsplit(result.url)
    return parsed.scheme in {"http", "https"} and parsed.hostname is not None


def _observation(
    result: MarginaliaSearchResult,
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
        source_id=MarginaliaSearchAdapter.source_id,
        adapter_id=MarginaliaSearchAdapter.adapter_id,
        adapter_version=MarginaliaSearchAdapter.adapter_version,
        collection_job_id=collection_job_id,
        source_record_type="marginalia-search-result",
        source_url=source_url,
        payload_hash_sha256=sha256(payload).hexdigest(),
        data_categories=frozenset({DataCategory.PUBLIC_RESULT_METADATA}),
        source_record_key=_record_key(query, result.url),
        collected_at=collected_at,
        retention_until=retention_until,
        schema_fingerprint="marginalia-search:v1",
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
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AdapterExecutionError(
            "invalid Marginalia Search checkpoint",
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

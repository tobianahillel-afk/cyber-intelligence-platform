from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from hashlib import sha256
from urllib.parse import urlsplit
from uuid import UUID

import httpx

from cip.adapters.sources.crossref_publications.client import (
    CrossrefClient,
    CrossrefClientError,
)
from cip.adapters.sources.crossref_publications.registry import CrossrefPublicationTarget
from cip.adapters.sources.crossref_publications.schemas import CrossrefWork
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.public_footprint.domain.search import SearchResultLead, map_search_result_lead
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    SourceRuntimeState,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_QUERY_TEMPLATE_ID = "crossref-ror-associated-works"
_QUERY_TEMPLATE_VERSION = 1


class CrossrefPublicationAdapter:
    source_id = "crossref-publication-metadata"
    adapter_id = "crossref-ror-works"
    adapter_version = "1"
    data_category = DataCategory.PUBLIC_RESULT_METADATA

    def __init__(
        self,
        entry: SourceRegistryEntry,
        targets: tuple[CrossrefPublicationTarget, ...],
        *,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("Crossref publication adapter requires its source policy")
        self._entry = entry
        self._targets = tuple(target for target in targets if target.enabled)
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
        target, next_index = _next_target(self._targets, checkpoint_payload)
        if target is None:
            return _empty_batch()
        _authorize(self._entry, collected_at)
        try:
            result = CrossrefClient(
                timeout_seconds=self._timeout_seconds,
                transport=self._transport,
            ).works_for_ror(self._entry.policy.base_url, ror_id=target.ror_id)
        except CrossrefClientError as exc:
            raise AdapterExecutionError(
                str(exc), error_code=exc.code, retryable=exc.retryable
            ) from exc
        items = tuple(item for item in result.response.message.items if _safe_work(item))
        observations = tuple(
            _observation(
                item,
                target=target,
                collection_job_id=collection_job_id,
                collected_at=collected_at,
                retention_until=retention_until,
                source_url=result.request_url,
            )
            for item in items
        )
        projections = tuple(
            map_search_result_lead(
                _lead(item, target=target, rank=rank, observed_at=collected_at)
            )
            for rank, item in enumerate(items, start=1)
        )
        return AdapterCollectionBatch(
            observations=observations,
            public_footprint_projections=projections,
            checkpoint_payload={"target_index": next_index},
            not_modified=not items,
        )


def _authorize(entry: SourceRegistryEntry, now: datetime) -> None:
    decision = entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.PUBLIC_RESULT_METADATA,
            target_url=entry.policy.base_url,
            purpose="publication-discovery",
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


def _next_target(
    targets: tuple[CrossrefPublicationTarget, ...],
    payload: Mapping[str, object] | None,
) -> tuple[CrossrefPublicationTarget | None, int]:
    if not targets:
        return None, 0
    value = 0 if payload is None else payload.get("target_index", 0)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise AdapterExecutionError(
            "invalid Crossref publication checkpoint",
            error_code="invalid_checkpoint",
            retryable=False,
        )
    index = value % len(targets)
    return targets[index], 0 if index + 1 >= len(targets) else index + 1


def _safe_work(item: CrossrefWork) -> bool:
    if not item.title or not item.title[0].strip():
        return False
    if any(character.isspace() for character in item.doi):
        return False
    parsed = urlsplit(item.url)
    return parsed.scheme == "https" and parsed.hostname == "doi.org"


def _lead(
    item: CrossrefWork,
    *,
    target: CrossrefPublicationTarget,
    rank: int,
    observed_at: datetime,
) -> SearchResultLead:
    title = item.title[0].strip()[:1_000]
    snippet = (
        f"Crossref metadata for DOI {item.doi}, type {item.type}; matched by ROR "
        f"{target.ror_id}. Authors, abstract and full text not retrieved."
    )
    return SearchResultLead(
        organization_id=target.organization_id,
        source_id=CrossrefPublicationAdapter.source_id,
        source_record_key=_record_key(target, item),
        target_url=item.url,
        title=title,
        snippet=snippet,
        rank=rank,
        observed_at=observed_at,
        query_template_id=_QUERY_TEMPLATE_ID,
        query_template_version=_QUERY_TEMPLATE_VERSION,
        candidate_claim=None,
    )


def _observation(
    item: CrossrefWork,
    *,
    target: CrossrefPublicationTarget,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    source_url: str,
) -> RawObservation:
    material = (
        f"{target.ror_id}\n{item.doi}\n{item.title[0].strip()}\n{item.type}\n{item.url}"
    ).encode()
    return RawObservation(
        source_id=CrossrefPublicationAdapter.source_id,
        adapter_id=CrossrefPublicationAdapter.adapter_id,
        adapter_version=CrossrefPublicationAdapter.adapter_version,
        collection_job_id=collection_job_id,
        source_record_type="crossref-ror-work-metadata",
        source_url=source_url,
        payload_hash_sha256=sha256(material).hexdigest(),
        data_categories=frozenset({DataCategory.PUBLIC_RESULT_METADATA}),
        source_record_key=_record_key(target, item),
        collected_at=collected_at,
        retention_until=retention_until,
        schema_fingerprint="crossref-ror-works:v1",
    )


def _record_key(target: CrossrefPublicationTarget, item: CrossrefWork) -> str:
    return f"{target.ror_id}:{item.doi.casefold()}"


def _empty_batch() -> AdapterCollectionBatch:
    return AdapterCollectionBatch(
        observations=(),
        public_footprint_projections=(),
        checkpoint_payload={"target_index": 0},
        not_modified=True,
    )

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date, datetime
from hashlib import sha256
from json import dumps
from urllib.parse import urlencode
from uuid import UUID

import httpx

from cip.adapters.sources.patentsview_patents.client import (
    PatentsViewClient,
    PatentsViewClientError,
)
from cip.adapters.sources.patentsview_patents.registry import PatentsViewPatentTarget
from cip.adapters.sources.patentsview_patents.schemas import PatentsViewPatent
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

_QUERY_TEMPLATE_ID = "patentsview-assignee-patents"
_QUERY_TEMPLATE_VERSION = 1


class PatentsViewPatentAdapter:
    source_id = "patentsview-patent-metadata"
    adapter_id = "patentsview-assignee-patents"
    adapter_version = "1"
    data_category = DataCategory.PUBLIC_RESULT_METADATA

    def __init__(
        self,
        entry: SourceRegistryEntry,
        targets: tuple[PatentsViewPatentTarget, ...],
        *,
        token_provider: Callable[[], str | None],
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("PatentsView patent adapter requires its source policy")
        self._entry = entry
        self._targets = tuple(target for target in targets if target.enabled)
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
        target, next_index = _next_target(self._targets, checkpoint_payload)
        if target is None:
            return _empty_batch()
        _authorize(self._entry, collected_at)
        token = self._token_provider()
        if token is None or not token.strip():
            raise AdapterExecutionError(
                "PatentsView provider is not connected",
                error_code="provider_not_connected",
                retryable=False,
            )
        try:
            result = PatentsViewClient(
                token,
                timeout_seconds=self._timeout_seconds,
                transport=self._transport,
            ).patents_for_assignee(
                self._entry.policy.base_url,
                assignee_organization=target.assignee_organization,
            )
        except PatentsViewClientError as exc:
            raise AdapterExecutionError(
                str(exc), error_code=exc.code, retryable=exc.retryable
            ) from exc
        items = tuple(
            item for item in result.response.patents if _belongs_to_target(item, target)
        )
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
                _lead(
                    item,
                    target=target,
                    rank=rank,
                    observed_at=collected_at,
                    base_url=self._entry.policy.base_url,
                )
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
            purpose="patent-discovery",
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
    targets: tuple[PatentsViewPatentTarget, ...],
    payload: Mapping[str, object] | None,
) -> tuple[PatentsViewPatentTarget | None, int]:
    if not targets:
        return None, 0
    value = 0 if payload is None else payload.get("target_index", 0)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise AdapterExecutionError(
            "invalid PatentsView patent checkpoint",
            error_code="invalid_checkpoint",
            retryable=False,
        )
    index = value % len(targets)
    return targets[index], 0 if index + 1 >= len(targets) else index + 1


def _belongs_to_target(item: PatentsViewPatent, target: PatentsViewPatentTarget) -> bool:
    try:
        date.fromisoformat(item.patent_date)
    except ValueError:
        return False
    if any(character.isspace() for character in item.patent_id):
        return False
    expected = target.assignee_organization.casefold()
    return any(
        assignee.assignee_organization is not None
        and assignee.assignee_organization.casefold() == expected
        for assignee in item.assignees
    )


def _lead(
    item: PatentsViewPatent,
    *,
    target: PatentsViewPatentTarget,
    rank: int,
    observed_at: datetime,
    base_url: str,
) -> SearchResultLead:
    target_url = _patent_locator(base_url, item.patent_id)
    snippet = (
        f"PatentsView metadata for US patent {item.patent_id}, granted {item.patent_date}, "
        f"type {item.patent_type}; matched configured assignee "
        f"{target.assignee_organization}. Abstract, claims, inventors and full text not retrieved."
    )
    return SearchResultLead(
        organization_id=target.organization_id,
        source_id=PatentsViewPatentAdapter.source_id,
        source_record_key=_record_key(target, item),
        target_url=target_url,
        title=item.patent_title.strip()[:1_000],
        snippet=snippet[:1_000],
        rank=rank,
        observed_at=observed_at,
        query_template_id=_QUERY_TEMPLATE_ID,
        query_template_version=_QUERY_TEMPLATE_VERSION,
        candidate_claim=None,
    )


def _observation(
    item: PatentsViewPatent,
    *,
    target: PatentsViewPatentTarget,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    source_url: str,
) -> RawObservation:
    material = (
        f"{target.assignee_organization}\n{item.patent_id}\n{item.patent_title.strip()}\n"
        f"{item.patent_date}\n{item.patent_type}"
    ).encode()
    return RawObservation(
        source_id=PatentsViewPatentAdapter.source_id,
        adapter_id=PatentsViewPatentAdapter.adapter_id,
        adapter_version=PatentsViewPatentAdapter.adapter_version,
        collection_job_id=collection_job_id,
        source_record_type="patentsview-assignee-patent-metadata",
        source_url=source_url,
        payload_hash_sha256=sha256(material).hexdigest(),
        data_categories=frozenset({DataCategory.PUBLIC_RESULT_METADATA}),
        source_record_key=_record_key(target, item),
        collected_at=collected_at,
        retention_until=retention_until,
        schema_fingerprint="patentsview-assignee-patents:v1",
    )


def _patent_locator(base_url: str, patent_id: str) -> str:
    query = dumps({"patent_id": patent_id}, separators=(",", ":"))
    return f"{base_url}?{urlencode({'q': query})}"


def _record_key(target: PatentsViewPatentTarget, item: PatentsViewPatent) -> str:
    return f"{target.target_id}:{item.patent_id}"


def _empty_batch() -> AdapterCollectionBatch:
    return AdapterCollectionBatch(
        observations=(),
        public_footprint_projections=(),
        checkpoint_payload={"target_index": 0},
        not_modified=True,
    )

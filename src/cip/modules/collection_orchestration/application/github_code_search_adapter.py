from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from hashlib import sha256
from urllib.parse import urlsplit
from uuid import UUID

import httpx

from cip.adapters.sources.developer_ecosystem.registry import (
    DeveloperEcosystemTarget,
    DeveloperTargetKind,
)
from cip.adapters.sources.github_code_search.client import (
    GitHubCodeSearchClient,
    GitHubCodeSearchClientError,
)
from cip.adapters.sources.github_code_search.schemas import GitHubCodeSearchItem
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


class GitHubCodeSearchAdapter:
    source_id = "github-code-search-metadata"
    adapter_id = "github-rest-code-search"
    adapter_version = "1"
    data_category = DataCategory.PUBLIC_RESULT_METADATA

    def __init__(
        self,
        entry: SourceRegistryEntry,
        targets: tuple[DeveloperEcosystemTarget, ...],
        templates: tuple[SearchQueryTemplate, ...],
        *,
        token_provider: Callable[[], str | None],
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("GitHub code-search adapter requires its source policy")
        self._entry = entry
        self._pairs = _pairs(targets, templates)
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
        token = self._token_provider()
        if not token:
            raise AdapterExecutionError(
                "GitHub code-search provider is not connected",
                error_code="provider_not_connected",
                retryable=False,
            )
        query = template.render(target.namespace or "")
        _authorize(self._entry, collected_at)
        try:
            result = GitHubCodeSearchClient(
                token,
                timeout_seconds=self._timeout_seconds,
                transport=self._transport,
            ).search(self._entry.policy.base_url, query=query)
        except GitHubCodeSearchClientError as exc:
            raise AdapterExecutionError(
                str(exc), error_code=exc.code, retryable=exc.retryable
            ) from exc
        items = tuple(
            item for item in result.response.items if _belongs_to_target(item, target)
        )
        observations = tuple(
            _observation(
                item,
                template=template,
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
                    template=template,
                    rank=index,
                    observed_at=collected_at,
                )
            )
            for index, item in enumerate(items, start=1)
        )
        return AdapterCollectionBatch(
            observations=observations,
            public_footprint_projections=projections,
            checkpoint_payload={"pair_index": next_index},
            not_modified=not items,
        )


def _authorize(entry: SourceRegistryEntry, now: datetime) -> None:
    decision = entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.PUBLIC_RESULT_METADATA,
            target_url=entry.policy.base_url,
            purpose="code-search-discovery",
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


def _pairs(
    targets: tuple[DeveloperEcosystemTarget, ...],
    templates: tuple[SearchQueryTemplate, ...],
) -> tuple[tuple[DeveloperEcosystemTarget, SearchQueryTemplate], ...]:
    return tuple(
        (target, template)
        for target in targets
        if target.enabled and target.kind is DeveloperTargetKind.GITHUB_ORG
        for template in templates
        if template.enabled
    )


def _next_pair(
    pairs: tuple[tuple[DeveloperEcosystemTarget, SearchQueryTemplate], ...],
    payload: Mapping[str, object] | None,
) -> tuple[tuple[DeveloperEcosystemTarget, SearchQueryTemplate] | None, int]:
    if not pairs:
        return None, 0
    value = 0 if payload is None else payload.get("pair_index", 0)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise AdapterExecutionError(
            "invalid GitHub code-search checkpoint",
            error_code="invalid_checkpoint",
            retryable=False,
        )
    index = value % len(pairs)
    next_index = 0 if index + 1 >= len(pairs) else index + 1
    return pairs[index], next_index


def _belongs_to_target(
    item: GitHubCodeSearchItem,
    target: DeveloperEcosystemTarget,
) -> bool:
    namespace = target.namespace or ""
    if item.repository.private:
        return False
    if not item.repository.full_name.casefold().startswith(f"{namespace.casefold()}/"):
        return False
    parsed = urlsplit(item.html_url)
    return parsed.scheme == "https" and parsed.hostname == "github.com"


def _lead(
    item: GitHubCodeSearchItem,
    *,
    target: DeveloperEcosystemTarget,
    template: SearchQueryTemplate,
    rank: int,
    observed_at: datetime,
) -> SearchResultLead:
    title = f"{item.repository.full_name}:{item.path}"
    snippet = (
        f"GitHub code-search metadata for {title} at {item.sha}; "
        "file content not retrieved."
    )
    return SearchResultLead(
        organization_id=target.organization_id,
        source_id=GitHubCodeSearchAdapter.source_id,
        source_record_key=_record_key(item, template),
        target_url=item.html_url,
        title=title,
        snippet=snippet,
        rank=rank,
        observed_at=observed_at,
        query_template_id=template.id,
        query_template_version=template.version,
        candidate_claim=None,
    )


def _observation(
    item: GitHubCodeSearchItem,
    *,
    template: SearchQueryTemplate,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    source_url: str,
) -> RawObservation:
    material = (
        f"{item.repository.full_name}\n{item.path}\n{item.sha}\n{item.html_url}\n{template.id}"
    ).encode()
    return RawObservation(
        source_id=GitHubCodeSearchAdapter.source_id,
        adapter_id=GitHubCodeSearchAdapter.adapter_id,
        adapter_version=GitHubCodeSearchAdapter.adapter_version,
        collection_job_id=collection_job_id,
        source_record_type="github-code-search-result-metadata",
        source_url=source_url,
        payload_hash_sha256=sha256(material).hexdigest(),
        data_categories=frozenset({DataCategory.PUBLIC_RESULT_METADATA}),
        source_record_key=_record_key(item, template),
        collected_at=collected_at,
        retention_until=retention_until,
        schema_fingerprint="github-rest-code-search:v1",
    )


def _record_key(item: GitHubCodeSearchItem, template: SearchQueryTemplate) -> str:
    return f"{template.id}:{item.repository.full_name}:{item.path}:{item.sha}"


def _empty_batch() -> AdapterCollectionBatch:
    return AdapterCollectionBatch(
        observations=(),
        public_footprint_projections=(),
        checkpoint_payload={"pair_index": 0},
        not_modified=True,
    )

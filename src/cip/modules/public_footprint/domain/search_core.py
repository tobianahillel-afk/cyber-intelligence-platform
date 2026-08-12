from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from cip.modules.public_footprint.domain.search import SearchQueryTemplate, SearchResultLead
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl
from cip.shared.kernel.time import require_aware_utc


class SearchAcquisitionState(StrEnum):
    UNROUTED = "unrouted"
    ROUTED_PUBLIC_WEB = "routed_public_web"
    REQUIRES_SOURCE_REVIEW = "requires_source_review"


@dataclass(frozen=True, slots=True)
class SearchQueryPlan:
    organization_id: UUID
    organization_name: str
    template_id: str
    template_version: int
    purpose: str
    rendered_query: str
    provider_ids: tuple[str, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        organization_name = _required_text(
            self.organization_name,
            field_name="organization_name",
            max_length=300,
        )
        template_id = _required_text(
            self.template_id,
            field_name="template_id",
            max_length=100,
        )
        purpose = _required_text(self.purpose, field_name="purpose", max_length=200)
        query = _required_text(
            self.rendered_query,
            field_name="rendered_query",
            max_length=500,
        )
        if self.template_version < 1:
            raise ValueError("search query template version must be positive")
        providers = _normalized_provider_ids(self.provider_ids)
        created_at = require_aware_utc(self.created_at, field_name="created_at")
        object.__setattr__(self, "organization_name", organization_name)
        object.__setattr__(self, "template_id", template_id)
        object.__setattr__(self, "purpose", purpose)
        object.__setattr__(self, "rendered_query", query)
        object.__setattr__(self, "provider_ids", providers)
        object.__setattr__(self, "created_at", created_at)

    @classmethod
    def from_template(
        cls,
        *,
        organization_id: UUID,
        organization_name: str,
        template: SearchQueryTemplate,
        provider_ids: tuple[str, ...],
        created_at: datetime,
        organization_domain: str | None = None,
    ) -> SearchQueryPlan:
        if not template.enabled:
            raise ValueError("search query template must be enabled before execution")
        return cls(
            organization_id=organization_id,
            organization_name=organization_name,
            template_id=template.id,
            template_version=template.version,
            purpose=template.purpose,
            rendered_query=template.render(
                organization_name,
                organization_domain=organization_domain,
            ),
            provider_ids=provider_ids,
            created_at=created_at,
        )


@dataclass(frozen=True, slots=True)
class SearchProviderExecution:
    provider_id: str
    organization_id: UUID
    rendered_query: str
    query_template_id: str
    query_template_version: int
    executed_at: datetime
    results: tuple[SearchResultLead, ...]

    def __post_init__(self) -> None:
        provider_id = _required_text(
            self.provider_id,
            field_name="provider_id",
            max_length=100,
        ).casefold()
        rendered_query = _required_text(
            self.rendered_query,
            field_name="rendered_query",
            max_length=500,
        )
        template_id = _required_text(
            self.query_template_id,
            field_name="query_template_id",
            max_length=100,
        )
        if self.query_template_version < 1:
            raise ValueError("search query template version must be positive")
        executed_at = require_aware_utc(self.executed_at, field_name="executed_at")
        if any(result.organization_id != self.organization_id for result in self.results):
            raise ValueError("search execution results must share the organization")
        if any(result.source_id.casefold() != provider_id for result in self.results):
            raise ValueError("search execution results must share the provider source id")
        if any(result.query_template_id != template_id for result in self.results):
            raise ValueError("search execution results must share the query template id")
        if any(
            result.query_template_version != self.query_template_version
            for result in self.results
        ):
            raise ValueError("search execution results must share the query template version")
        object.__setattr__(self, "provider_id", provider_id)
        object.__setattr__(self, "rendered_query", rendered_query)
        object.__setattr__(self, "query_template_id", template_id)
        object.__setattr__(self, "executed_at", executed_at)


@dataclass(frozen=True, slots=True)
class SearchProviderHit:
    provider_id: str
    source_record_key: str
    rank: int
    observed_at: datetime
    executed_at: datetime
    title: str
    snippet: str
    rendered_query: str
    query_template_id: str
    query_template_version: int

    def __post_init__(self) -> None:
        provider_id = _required_text(
            self.provider_id,
            field_name="provider_id",
            max_length=100,
        ).casefold()
        record_key = _required_text(
            self.source_record_key,
            field_name="source_record_key",
            max_length=500,
        )
        title = _required_text(self.title, field_name="title", max_length=1_000)
        snippet = _required_text(self.snippet, field_name="snippet", max_length=1_000)
        rendered_query = _required_text(
            self.rendered_query,
            field_name="rendered_query",
            max_length=500,
        )
        template_id = _required_text(
            self.query_template_id,
            field_name="query_template_id",
            max_length=100,
        )
        if not 1 <= self.rank <= 1_000:
            raise ValueError("search result rank must be between 1 and 1000")
        if self.query_template_version < 1:
            raise ValueError("search query template version must be positive")
        observed_at = require_aware_utc(self.observed_at, field_name="observed_at")
        executed_at = require_aware_utc(self.executed_at, field_name="executed_at")
        object.__setattr__(self, "provider_id", provider_id)
        object.__setattr__(self, "source_record_key", record_key)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "snippet", snippet)
        object.__setattr__(self, "rendered_query", rendered_query)
        object.__setattr__(self, "query_template_id", template_id)
        object.__setattr__(self, "observed_at", observed_at)
        object.__setattr__(self, "executed_at", executed_at)


@dataclass(frozen=True, slots=True)
class SearchDiscoveryCandidate:
    organization_id: UUID
    target_url: str
    title: str
    snippet: str
    purpose: str
    provider_hits: tuple[SearchProviderHit, ...]
    acquisition_state: SearchAcquisitionState = SearchAcquisitionState.UNROUTED

    def __post_init__(self) -> None:
        target_url = CanonicalUrl(self.target_url).value
        title = _required_text(self.title, field_name="title", max_length=1_000)
        snippet = _required_text(self.snippet, field_name="snippet", max_length=1_000)
        purpose = _required_text(self.purpose, field_name="purpose", max_length=200)
        if not self.provider_hits:
            raise ValueError("search discovery candidate requires provider provenance")
        provider_hits = tuple(sorted(self.provider_hits, key=_hit_sort_key))
        object.__setattr__(self, "target_url", target_url)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "snippet", snippet)
        object.__setattr__(self, "purpose", purpose)
        object.__setattr__(self, "provider_hits", provider_hits)

    @property
    def provider_count(self) -> int:
        return len({hit.provider_id for hit in self.provider_hits})

    @property
    def best_rank(self) -> int:
        return min(hit.rank for hit in self.provider_hits)


def normalize_search_executions(
    plan: SearchQueryPlan,
    executions: tuple[SearchProviderExecution, ...],
) -> tuple[SearchDiscoveryCandidate, ...]:
    _validate_executions(plan, executions)
    grouped: dict[str, list[SearchProviderHit]] = {}
    for execution in executions:
        for result in execution.results:
            canonical_url = CanonicalUrl(result.target_url).value
            grouped.setdefault(canonical_url, []).append(_provider_hit(execution, result))
    candidates = tuple(
        _candidate_from_hits(plan, target_url, tuple(hits))
        for target_url, hits in grouped.items()
    )
    return tuple(sorted(candidates, key=_candidate_sort_key))


def _validate_executions(
    plan: SearchQueryPlan,
    executions: tuple[SearchProviderExecution, ...],
) -> None:
    provider_ids = [execution.provider_id for execution in executions]
    if len(provider_ids) != len(set(provider_ids)):
        raise ValueError("search plan accepts at most one execution per provider")
    unknown = set(provider_ids) - set(plan.provider_ids)
    if unknown:
        raise ValueError("search execution provider is not part of the query plan")
    for execution in executions:
        if execution.organization_id != plan.organization_id:
            raise ValueError("search execution organization does not match the query plan")
        if execution.rendered_query != plan.rendered_query:
            raise ValueError("search execution query does not match the query plan")
        if execution.query_template_id != plan.template_id:
            raise ValueError("search execution template does not match the query plan")
        if execution.query_template_version != plan.template_version:
            raise ValueError("search execution template version does not match the query plan")


def _provider_hit(
    execution: SearchProviderExecution,
    result: SearchResultLead,
) -> SearchProviderHit:
    return SearchProviderHit(
        provider_id=execution.provider_id,
        source_record_key=result.source_record_key,
        rank=result.rank,
        observed_at=result.observed_at,
        executed_at=execution.executed_at,
        title=result.title,
        snippet=result.snippet,
        rendered_query=execution.rendered_query,
        query_template_id=execution.query_template_id,
        query_template_version=execution.query_template_version,
    )


def _candidate_from_hits(
    plan: SearchQueryPlan,
    target_url: str,
    hits: tuple[SearchProviderHit, ...],
) -> SearchDiscoveryCandidate:
    ordered_hits = tuple(sorted(hits, key=_hit_sort_key))
    representative = ordered_hits[0]
    return SearchDiscoveryCandidate(
        organization_id=plan.organization_id,
        target_url=target_url,
        title=representative.title,
        snippet=representative.snippet,
        purpose=plan.purpose,
        provider_hits=ordered_hits,
    )


def _hit_sort_key(hit: SearchProviderHit) -> tuple[int, str, str]:
    return (hit.rank, hit.provider_id, hit.source_record_key)


def _candidate_sort_key(candidate: SearchDiscoveryCandidate) -> tuple[int, str]:
    return (candidate.best_rank, candidate.target_url)


def _normalized_provider_ids(values: tuple[str, ...]) -> tuple[str, ...]:
    providers = tuple(
        dict.fromkeys(
            _required_text(value, field_name="provider_id", max_length=100).casefold()
            for value in values
        )
    )
    if not providers:
        raise ValueError("search query plan requires at least one provider")
    if len(providers) != len(values):
        raise ValueError("search query plan provider ids must be unique")
    return providers


def _required_text(value: str, *, field_name: str, max_length: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} cannot exceed {max_length} characters")
    return normalized

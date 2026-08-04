from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from uuid import UUID

from pydantic import ValidationError

from cip.adapters.sources.smartrecruiters.client import SmartRecruitersClient
from cip.adapters.sources.smartrecruiters.mapper import (
    map_smartrecruiters_posting,
    smartrecruiters_posting_to_canonical,
)
from cip.adapters.sources.smartrecruiters.registry import SmartRecruitersCompany
from cip.adapters.sources.smartrecruiters.schemas import (
    SmartRecruitersPostingDetail,
    SmartRecruitersPostingList,
    SmartRecruitersPostingSummary,
)
from cip.modules.collection_orchestration.application.ports import CommercialProjection
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    SourceRuntimeState,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.kernel.time import require_aware_utc


class SmartRecruitersCollectionDeniedError(RuntimeError):
    """Source governance denied SmartRecruiters collection."""


class SmartRecruitersSourceSchemaError(RuntimeError):
    """SmartRecruiters payload no longer matches the approved schema."""


class SmartRecruitersSourceWindowError(RuntimeError):
    """A SmartRecruiters company exceeds the configured safe job count."""


@dataclass(frozen=True, slots=True)
class SmartRecruitersCheckpoint:
    fingerprints: Mapping[str, Mapping[str, str]]

    def __post_init__(self) -> None:
        copied = {
            company_id: MappingProxyType(dict(values))
            for company_id, values in self.fingerprints.items()
        }
        object.__setattr__(self, "fingerprints", MappingProxyType(copied))


@dataclass(frozen=True, slots=True)
class SmartRecruitersCollectionBatch:
    observations: tuple[RawObservation, ...]
    projections: tuple[CommercialProjection, ...]
    checkpoint: SmartRecruitersCheckpoint
    not_modified: bool


def collect_smartrecruiters_jobs(
    client: SmartRecruitersClient,
    entry: SourceRegistryEntry,
    companies: tuple[SmartRecruitersCompany, ...],
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    checkpoint: SmartRecruitersCheckpoint | None = None,
    page_size: int = 100,
    max_jobs_per_company: int = 5_000,
) -> SmartRecruitersCollectionBatch:
    collected = require_aware_utc(collected_at, field_name="collected_at")
    enabled_companies = tuple(company for company in companies if company.enabled)
    if not enabled_companies:
        raise ValueError("at least one SmartRecruiters company must be enabled")
    if not 1 <= page_size <= 100:
        raise ValueError("page_size must be between 1 and 100")
    if max_jobs_per_company < 1:
        raise ValueError("max_jobs_per_company must be positive")
    previous = checkpoint.fingerprints if checkpoint else {}
    current: dict[str, dict[str, str]] = {}
    observations: list[RawObservation] = []
    projections: list[CommercialProjection] = []

    for company in enabled_companies:
        summaries = _fetch_summaries(
            client,
            entry,
            company,
            collected_at=collected,
            page_size=page_size,
            max_jobs=max_jobs_per_company,
        )
        current[company.id] = _collect_company(
            client,
            entry,
            company,
            summaries,
            previous=previous.get(company.id, {}),
            collection_job_id=collection_job_id,
            collected_at=collected,
            retention_until=retention_until,
            observations=observations,
            projections=projections,
        )

    current_checkpoint = SmartRecruitersCheckpoint(current)
    return SmartRecruitersCollectionBatch(
        observations=tuple(observations),
        projections=tuple(projections),
        checkpoint=current_checkpoint,
        not_modified=_checkpoint_equal(previous, current_checkpoint.fingerprints),
    )


def _fetch_summaries(
    client: SmartRecruitersClient,
    entry: SourceRegistryEntry,
    company: SmartRecruitersCompany,
    *,
    collected_at: datetime,
    page_size: int,
    max_jobs: int,
) -> tuple[SmartRecruitersPostingSummary, ...]:
    summaries: list[SmartRecruitersPostingSummary] = []
    offset = 0
    while True:
        list_url = client.postings_url(company.company_identifier)
        _authorize(entry, list_url, collected_at=collected_at)
        page = _parse_list(
            client.fetch_postings(
                company.company_identifier,
                offset=offset,
                limit=page_size,
            ).body
        )
        if page.offset != offset:
            raise SmartRecruitersSourceSchemaError("unexpected pagination offset")
        if page.total_found > max_jobs:
            raise SmartRecruitersSourceWindowError(
                "SmartRecruiters company exceeds configured job limit"
            )
        summaries.extend(page.content)
        if len(summaries) > max_jobs:
            raise SmartRecruitersSourceWindowError(
                "SmartRecruiters company exceeds configured job limit"
            )
        offset += len(page.content)
        if offset >= page.total_found:
            return tuple(summaries)
        if not page.content:
            raise SmartRecruitersSourceSchemaError(
                "SmartRecruiters pagination stopped before totalFound"
            )


def _collect_company(
    client: SmartRecruitersClient,
    entry: SourceRegistryEntry,
    company: SmartRecruitersCompany,
    summaries: tuple[SmartRecruitersPostingSummary, ...],
    *,
    previous: Mapping[str, str],
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    observations: list[RawObservation],
    projections: list[CommercialProjection],
) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for summary in summaries:
        if summary.id in fingerprints:
            raise SmartRecruitersSourceSchemaError(
                f"duplicate posting id for company {company.id}: {summary.id}"
            )
        detail_url = client.posting_url(company.company_identifier, summary.id)
        _authorize(entry, detail_url, collected_at=collected_at)
        detail = _parse_detail(
            client.fetch_posting(company.company_identifier, summary.id).body
        )
        _validate_detail(summary, detail)
        fingerprint = smartrecruiters_posting_to_canonical(
            company,
            summary,
            detail,
        ).fingerprint()
        fingerprints[summary.id] = fingerprint
        mapped = map_smartrecruiters_posting(
            company,
            summary,
            detail,
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
        )
        if mapped is None:
            continue
        observation, projection = mapped
        projections.append(projection)
        if previous.get(summary.id) != fingerprint:
            observations.append(observation)
    return fingerprints


def _authorize(entry: SourceRegistryEntry, target_url: str, *, collected_at: datetime) -> None:
    decision = entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.PUBLIC_JOB_POSTING,
            target_url=target_url,
            purpose="commercial-hiring-intelligence",
            automated=True,
            store_raw_content=False,
            human_review_completed=False,
        ),
        entry.authorization,
        SourceRuntimeState(remaining_requests=1),
        now=collected_at,
    )
    if not decision.allowed:
        raise SmartRecruitersCollectionDeniedError(decision.reason.value)


def _parse_list(body: bytes) -> SmartRecruitersPostingList:
    try:
        return SmartRecruitersPostingList.model_validate_json(body)
    except ValidationError as exc:
        raise SmartRecruitersSourceSchemaError(
            "SmartRecruiters list schema validation failed"
        ) from exc


def _parse_detail(body: bytes) -> SmartRecruitersPostingDetail:
    try:
        return SmartRecruitersPostingDetail.model_validate_json(body)
    except ValidationError as exc:
        raise SmartRecruitersSourceSchemaError(
            "SmartRecruiters detail schema validation failed"
        ) from exc


def _validate_detail(
    summary: SmartRecruitersPostingSummary,
    detail: SmartRecruitersPostingDetail,
) -> None:
    if summary.id != detail.id:
        raise SmartRecruitersSourceSchemaError(
            "SmartRecruiters detail id does not match list item"
        )


def _checkpoint_equal(
    previous: Mapping[str, Mapping[str, str]],
    current: Mapping[str, Mapping[str, str]],
) -> bool:
    return {
        company_id: dict(values) for company_id, values in previous.items()
    } == {company_id: dict(values) for company_id, values in current.items()}

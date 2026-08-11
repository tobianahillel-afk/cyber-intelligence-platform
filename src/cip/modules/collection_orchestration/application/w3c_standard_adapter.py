from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from hashlib import sha256
from urllib.parse import urlsplit
from uuid import UUID

import httpx

from cip.adapters.sources.w3c_standards.client import (
    W3cClient,
    W3cClientError,
    W3cSpecificationRecord,
)
from cip.adapters.sources.w3c_standards.registry import W3cAffiliationTarget
from cip.adapters.sources.w3c_standards.schemas import W3cSpecification
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

_QUERY_TEMPLATE_ID = "w3c-affiliation-group-specifications"
_QUERY_TEMPLATE_VERSION = 1


class W3cStandardAdapter:
    source_id = "w3c-affiliation-specification-metadata"
    adapter_id = "w3c-affiliation-specifications"
    adapter_version = "1"
    data_category = DataCategory.PUBLIC_RESULT_METADATA

    def __init__(
        self,
        entry: SourceRegistryEntry,
        targets: tuple[W3cAffiliationTarget, ...],
        *,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("W3C standards adapter requires its source policy")
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
            result = W3cClient(
                timeout_seconds=self._timeout_seconds,
                transport=self._transport,
            ).specifications_for_affiliation(
                self._entry.policy.base_url,
                affiliation_id=target.affiliation_id,
            )
        except W3cClientError as exc:
            raise AdapterExecutionError(
                str(exc), error_code=exc.code, retryable=exc.retryable
            ) from exc
        if _normalize_name(result.affiliation.name) != _normalize_name(target.canonical_name):
            raise AdapterExecutionError(
                "W3C affiliation identity did not match configured organization target",
                error_code="target_identity_mismatch",
                retryable=False,
            )
        records = tuple(record for record in result.records if _safe_record(record))
        observations = tuple(
            _observation(
                record,
                target=target,
                collection_job_id=collection_job_id,
                collected_at=collected_at,
                retention_until=retention_until,
            )
            for record in records
        )
        projections = tuple(
            map_search_result_lead(
                _lead(record, target=target, rank=rank, observed_at=collected_at)
            )
            for rank, record in enumerate(records, start=1)
        )
        return AdapterCollectionBatch(
            observations=observations,
            public_footprint_projections=projections,
            checkpoint_payload={"target_index": next_index},
            not_modified=not records,
        )


def _authorize(entry: SourceRegistryEntry, now: datetime) -> None:
    decision = entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.PUBLIC_RESULT_METADATA,
            target_url=entry.policy.base_url,
            purpose="standards-discovery",
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
    targets: tuple[W3cAffiliationTarget, ...],
    payload: Mapping[str, object] | None,
) -> tuple[W3cAffiliationTarget | None, int]:
    if not targets:
        return None, 0
    value = 0 if payload is None else payload.get("target_index", 0)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise AdapterExecutionError(
            "invalid W3C standards checkpoint",
            error_code="invalid_checkpoint",
            retryable=False,
        )
    index = value % len(targets)
    return targets[index], 0 if index + 1 >= len(targets) else index + 1


def _safe_record(record: W3cSpecificationRecord) -> bool:
    return _specification_url(record.specification) is not None


def _lead(
    record: W3cSpecificationRecord,
    *,
    target: W3cAffiliationTarget,
    rank: int,
    observed_at: datetime,
) -> SearchResultLead:
    specification = record.specification
    target_url = _specification_url(specification)
    if target_url is None:
        raise ValueError("W3C specification has no safe metadata URL")
    snippet = (
        f"W3C public metadata links affiliation {target.affiliation_id} "
        f"({target.canonical_name}) to group {record.group_type}/{record.group_shortname}, "
        f"which lists specification {specification.shortname}. Participants, editors, versions "
        "and specification body were not retrieved."
    )
    return SearchResultLead(
        organization_id=target.organization_id,
        source_id=W3cStandardAdapter.source_id,
        source_record_key=_record_key(target, record),
        target_url=target_url,
        title=specification.title[:1_000],
        snippet=snippet,
        rank=rank,
        observed_at=observed_at,
        query_template_id=_QUERY_TEMPLATE_ID,
        query_template_version=_QUERY_TEMPLATE_VERSION,
        candidate_claim=None,
    )


def _observation(
    record: W3cSpecificationRecord,
    *,
    target: W3cAffiliationTarget,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
) -> RawObservation:
    specification = record.specification
    target_url = _specification_url(specification)
    if target_url is None:
        raise ValueError("W3C specification has no safe metadata URL")
    material = (
        f"{target.affiliation_id}\n{target.canonical_name}\n{record.group_type}\n"
        f"{record.group_shortname}\n{specification.shortname}\n{specification.title}\n"
        f"{target_url}"
    ).encode()
    return RawObservation(
        source_id=W3cStandardAdapter.source_id,
        adapter_id=W3cStandardAdapter.adapter_id,
        adapter_version=W3cStandardAdapter.adapter_version,
        collection_job_id=collection_job_id,
        source_record_type="w3c-affiliation-group-specification-metadata",
        source_url=record.source_url,
        payload_hash_sha256=sha256(material).hexdigest(),
        data_categories=frozenset({DataCategory.PUBLIC_RESULT_METADATA}),
        source_record_key=_record_key(target, record),
        collected_at=collected_at,
        retention_until=retention_until,
        schema_fingerprint="w3c-affiliation-specifications:v1",
    )


def _record_key(target: W3cAffiliationTarget, record: W3cSpecificationRecord) -> str:
    return (
        f"{target.affiliation_id}:{record.group_type}:{record.group_shortname.casefold()}:"
        f"{record.specification.shortname.casefold()}"
    )


def _specification_url(specification: W3cSpecification) -> str | None:
    if specification.shortlink:
        parsed = urlsplit(specification.shortlink)
        if parsed.scheme == "https" and parsed.hostname in {"w3.org", "www.w3.org"}:
            return specification.shortlink
    self_link = specification.links.get("self")
    if self_link is None:
        return None
    parsed = urlsplit(self_link.href)
    if (
        parsed.scheme == "https"
        and parsed.hostname == "api.w3.org"
        and parsed.path.startswith("/specifications/")
        and not parsed.query
        and not parsed.fragment
    ):
        return self_link.href
    return None


def _normalize_name(value: str) -> str:
    return " ".join(value.split()).casefold()


def _empty_batch() -> AdapterCollectionBatch:
    return AdapterCollectionBatch(
        observations=(),
        public_footprint_projections=(),
        checkpoint_payload={"target_index": 0},
        not_modified=True,
    )

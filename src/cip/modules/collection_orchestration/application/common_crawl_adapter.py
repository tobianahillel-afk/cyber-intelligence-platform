from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from hashlib import sha256
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from pydantic import ValidationError

from cip.adapters.sources.common_crawl.schemas import (
    CommonCrawlCapture,
    CommonCrawlCollection,
    crawl_sort_key,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.public_footprint.domain.archive import (
    CommonCrawlIndexLead,
    map_common_crawl_index_lead,
)
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    SourceRuntimeState,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_MAX_CAPTURES = 50
_FIELDS = ("timestamp", "url", "mime", "status", "digest", "length", "offset", "filename")
_USER_AGENT = (
    "cyber-intelligence-platform/0.24 "
    "(+https://github.com/tobianahillel-afk/cyber-intelligence-platform)"
)


class CommonCrawlIndexAdapter:
    source_id = "common-crawl-index"
    adapter_id = "common-crawl-cdxj-index"
    adapter_version = "1"
    data_category = DataCategory.PUBLIC_RESULT_METADATA

    def __init__(
        self,
        entry: SourceRegistryEntry,
        targets: tuple[PublicWebTarget, ...],
        *,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("Common Crawl adapter requires common-crawl-index policy")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._entry = entry
        self._pairs = _target_prefix_pairs(targets)
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
        pair, next_index, crawl_ids = _next_pair(self._pairs, checkpoint_payload)
        if pair is None:
            return _empty_batch()
        target, prefix = pair
        collection_url = self._entry.policy.base_url
        _authorize(self._entry, collection_url, collected_at)
        collections = _fetch_collections(
            collection_url,
            timeout_seconds=self._timeout_seconds,
            transport=self._transport,
        )
        collection = max(collections, key=lambda item: crawl_sort_key(item.id))
        _validate_collection_endpoint(collection)
        previous_crawl = crawl_ids.get(_pair_key(target, prefix))
        if previous_crawl == collection.id:
            return _checkpoint_batch(next_index, crawl_ids, target, prefix, collection.id)
        _authorize(self._entry, collection.cdx_api, collected_at)
        body, request_url = _fetch_captures(
            collection.cdx_api,
            url_pattern=_target_pattern(target, prefix),
            timeout_seconds=self._timeout_seconds,
            transport=self._transport,
        )
        captures = tuple(
            capture
            for capture in _parse_captures(body)
            if _capture_in_scope(capture, target)
        )
        observations = tuple(
            _observation(
                capture,
                collection_id=collection.id,
                collection_job_id=collection_job_id,
                collected_at=collected_at,
                retention_until=retention_until,
                source_url=request_url,
            )
            for capture in captures
        )
        projections = tuple(
            map_common_crawl_index_lead(
                _lead(
                    capture,
                    collection_id=collection.id,
                    target=target,
                    observed_at=collected_at,
                    index_url=collection.cdx_api,
                )
            )
            for capture in captures
        )
        next_crawl_ids = dict(crawl_ids)
        next_crawl_ids[_pair_key(target, prefix)] = collection.id
        return AdapterCollectionBatch(
            observations=observations,
            public_footprint_projections=projections,
            checkpoint_payload={"pair_index": next_index, "crawl_ids": next_crawl_ids},
            not_modified=not captures,
        )


def _authorize(entry: SourceRegistryEntry, target_url: str, now: datetime) -> None:
    decision = entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.PUBLIC_RESULT_METADATA,
            target_url=target_url,
            purpose="archive-discovery",
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


def _fetch_collections(
    url: str,
    *,
    timeout_seconds: float,
    transport: httpx.BaseTransport | None,
) -> tuple[CommonCrawlCollection, ...]:
    body, _ = _get(url, timeout_seconds=timeout_seconds, transport=transport)
    try:
        raw = json.loads(body)
        if not isinstance(raw, list) or not raw:
            raise ValueError("collection list must be non-empty")
        return tuple(CommonCrawlCollection.model_validate(item) for item in raw)
    except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as exc:
        raise _schema_error("Common Crawl collection metadata changed", exc) from exc


def _fetch_captures(
    url: str,
    *,
    url_pattern: str,
    timeout_seconds: float,
    transport: httpx.BaseTransport | None,
) -> tuple[bytes, str]:
    params: dict[str, str | int] = {
        "url": url_pattern,
        "output": "json",
        "filter": "status:200",
        "collapse": "digest",
        "limit": _MAX_CAPTURES,
        "fl": ",".join(_FIELDS),
    }
    return _get(url, params=params, timeout_seconds=timeout_seconds, transport=transport)


def _get(
    url: str,
    *,
    params: Mapping[str, str | int] | None = None,
    timeout_seconds: float,
    transport: httpx.BaseTransport | None,
) -> tuple[bytes, str]:
    try:
        with httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=False,
            transport=transport,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise AdapterExecutionError(
            f"Common Crawl returned HTTP {status}",
            error_code=f"http_{status}",
            retryable=status == 429 or status >= 500,
        ) from exc
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise AdapterExecutionError(
            str(exc) or type(exc).__name__,
            error_code="source_transport_error",
            retryable=True,
        ) from exc
    if len(response.content) > _MAX_RESPONSE_BYTES:
        raise AdapterExecutionError(
            "Common Crawl response exceeds size limit",
            error_code="unsafe_source_response",
            retryable=False,
        )
    return response.content, str(response.url)


def _parse_captures(body: bytes) -> tuple[CommonCrawlCapture, ...]:
    captures: list[CommonCrawlCapture] = []
    for line in body.decode("utf-8").splitlines()[:_MAX_CAPTURES]:
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            captures.append(CommonCrawlCapture.model_validate(raw))
        except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as exc:
            raise _schema_error("Common Crawl capture metadata changed", exc) from exc
    return tuple(captures)


def _validate_collection_endpoint(collection: CommonCrawlCollection) -> None:
    parsed = urlsplit(collection.cdx_api)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "index.commoncrawl.org"
        or parsed.path != f"/{collection.id}-index"
        or parsed.query
        or parsed.fragment
    ):
        raise AdapterExecutionError(
            "Common Crawl collection endpoint is outside approved shape",
            error_code="unsafe_source_response",
            retryable=False,
        )


def _capture_in_scope(capture: CommonCrawlCapture, target: PublicWebTarget) -> bool:
    return target.crawl_scope.evaluate_target(
        capture.url,
        depth=0,
        redirects=0,
        usage=CrawlUsage(),
    ).allowed


def _target_prefix_pairs(
    targets: tuple[PublicWebTarget, ...],
) -> tuple[tuple[PublicWebTarget, str], ...]:
    return tuple(
        (target, prefix)
        for target in targets
        if target.enabled
        for prefix in target.allowed_path_prefixes
    )


def _target_pattern(target: PublicWebTarget, prefix: str) -> str:
    parsed = urlsplit(target.base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return f"{origin}/*" if prefix == "/" else f"{origin}{prefix}/*"


def _next_pair(
    pairs: tuple[tuple[PublicWebTarget, str], ...],
    payload: Mapping[str, object] | None,
) -> tuple[tuple[PublicWebTarget, str] | None, int, dict[str, str]]:
    if not pairs:
        return None, 0, {}
    index_value = 0 if payload is None else payload.get("pair_index", 0)
    crawl_value = {} if payload is None else payload.get("crawl_ids", {})
    if not isinstance(index_value, int) or isinstance(index_value, bool) or index_value < 0:
        raise _checkpoint_error()
    if not isinstance(crawl_value, dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in crawl_value.items()
    ):
        raise _checkpoint_error()
    valid_keys = {_pair_key(target, prefix) for target, prefix in pairs}
    crawl_ids = {
        key: value for key, value in crawl_value.items() if key in valid_keys
    }
    index = index_value % len(pairs)
    next_index = 0 if index + 1 >= len(pairs) else index + 1
    return pairs[index], next_index, crawl_ids


def _pair_key(target: PublicWebTarget, prefix: str) -> str:
    return f"{target.id}:{prefix}"


def _checkpoint_batch(
    next_index: int,
    crawl_ids: dict[str, str],
    target: PublicWebTarget,
    prefix: str,
    crawl_id: str,
) -> AdapterCollectionBatch:
    next_crawl_ids = dict(crawl_ids)
    next_crawl_ids[_pair_key(target, prefix)] = crawl_id
    return AdapterCollectionBatch(
        observations=(),
        public_footprint_projections=(),
        checkpoint_payload={"pair_index": next_index, "crawl_ids": next_crawl_ids},
        not_modified=True,
    )


def _lead(
    capture: CommonCrawlCapture,
    *,
    collection_id: str,
    target: PublicWebTarget,
    observed_at: datetime,
    index_url: str,
) -> CommonCrawlIndexLead:
    capture_at = datetime.strptime(capture.timestamp, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
    return CommonCrawlIndexLead(
        organization_id=target.organization_id,
        source_id=CommonCrawlIndexAdapter.source_id,
        source_record_key=f"{collection_id}:{capture.timestamp}:{capture.digest}",
        original_url=capture.url,
        index_url=index_url,
        crawl_id=collection_id,
        capture_at=capture_at,
        observed_at=observed_at,
        archived_mime_type=capture.mime,
        archived_status_code=int(capture.status),
        archived_length=capture.length,
        archived_digest=capture.digest,
        warc_filename=capture.filename,
        warc_offset=capture.offset,
        warc_record_length=capture.length,
    )


def _observation(
    capture: CommonCrawlCapture,
    *,
    collection_id: str,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    source_url: str,
) -> RawObservation:
    encoded = capture.model_dump_json().encode("utf-8")
    return RawObservation(
        source_id=CommonCrawlIndexAdapter.source_id,
        adapter_id=CommonCrawlIndexAdapter.adapter_id,
        adapter_version=CommonCrawlIndexAdapter.adapter_version,
        collection_job_id=collection_job_id,
        source_record_type="common-crawl-index-capture",
        source_url=source_url,
        payload_hash_sha256=sha256(encoded).hexdigest(),
        data_categories=frozenset({DataCategory.PUBLIC_RESULT_METADATA}),
        source_record_key=f"{collection_id}:{capture.timestamp}:{capture.digest}",
        collected_at=collected_at,
        retention_until=retention_until,
        schema_fingerprint="common-crawl-cdxj:v1",
    )


def _schema_error(message: str, exc: Exception) -> AdapterExecutionError:
    return AdapterExecutionError(message, error_code="source_schema_drift", retryable=False)


def _checkpoint_error() -> AdapterExecutionError:
    return AdapterExecutionError(
        "invalid Common Crawl checkpoint",
        error_code="invalid_checkpoint",
        retryable=False,
    )


def _empty_batch() -> AdapterCollectionBatch:
    return AdapterCollectionBatch(
        observations=(),
        public_footprint_projections=(),
        checkpoint_payload={"pair_index": 0, "crawl_ids": {}},
        not_modified=True,
    )
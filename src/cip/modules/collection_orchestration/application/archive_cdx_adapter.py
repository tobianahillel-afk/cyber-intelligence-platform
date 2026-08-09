from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

import httpx
from pydantic import ValidationError

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.adapters.sources.search_archives.schemas import ArchiveCapture
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterExecutionError,
)
from cip.modules.public_footprint.domain.archive import (
    ArchiveCaptureLead,
    map_archive_capture_lead,
)
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    SourceRuntimeState,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_MAX_CAPTURES = 50
_FIELDS = ("timestamp", "original", "mimetype", "statuscode", "digest", "length")


class InternetArchiveCdxAdapter:
    source_id = "internet-archive-cdx"
    adapter_id = "internet-archive-cdx"
    adapter_version = "1"
    data_category = DataCategory.OFFICIAL_DOCUMENT_DISCOVERY

    def __init__(
        self,
        entry: SourceRegistryEntry,
        targets: tuple[PublicWebTarget, ...],
        *,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if entry.policy.id != self.source_id:
            raise ValueError("archive adapter requires internet-archive-cdx policy")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
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
        target_url = self._entry.policy.base_url
        _authorize(self._entry, target_url, collected_at)
        body = _request(
            target_url,
            archived_url=target.base_url,
            timeout_seconds=self._timeout_seconds,
            transport=self._transport,
        )
        captures = _parse_cdx(body)
        observations = tuple(
            _observation(
                capture,
                collection_job_id=collection_job_id,
                collected_at=collected_at,
                retention_until=retention_until,
                source_url=target_url,
            )
            for capture in captures
        )
        projections = tuple(
            map_archive_capture_lead(
                _lead(capture, target=target, observed_at=collected_at)
            )
            for capture in captures
        )
        return AdapterCollectionBatch(
            observations=observations,
            public_footprint_projections=projections,
            checkpoint_payload={"target_index": next_index},
            not_modified=not captures,
        )


def _authorize(entry: SourceRegistryEntry, target_url: str, now: datetime) -> None:
    decision = entry.policy.evaluate(
        CollectionRequest(
            data_category=DataCategory.OFFICIAL_DOCUMENT_DISCOVERY,
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


def _request(
    target_url: str,
    *,
    archived_url: str,
    timeout_seconds: float,
    transport: httpx.BaseTransport | None,
) -> bytes:
    params: dict[str, str | int] = {
        "url": archived_url,
        "output": "json",
        "fl": ",".join(_FIELDS),
        "filter": "statuscode:200",
        "collapse": "digest",
        "limit": _MAX_CAPTURES,
    }
    try:
        with httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=False,
            transport=transport,
        ) as client:
            response = client.get(target_url, params=params)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise AdapterExecutionError(
            f"archive provider returned HTTP {status}",
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
            "archive provider response is not JSON",
            error_code="unsafe_source_response",
            retryable=False,
        )
    if len(response.content) > _MAX_RESPONSE_BYTES:
        raise AdapterExecutionError(
            "archive provider response exceeds size limit",
            error_code="unsafe_source_response",
            retryable=False,
        )
    return response.content


def _parse_cdx(body: bytes) -> tuple[ArchiveCapture, ...]:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise AdapterExecutionError(
            "archive provider returned invalid JSON",
            error_code="source_schema_drift",
            retryable=False,
        ) from exc
    if not isinstance(payload, list) or not payload:
        return ()
    header = payload[0]
    if not isinstance(header, list) or tuple(header) != _FIELDS:
        raise AdapterExecutionError(
            "archive provider fields changed",
            error_code="source_schema_drift",
            retryable=False,
        )
    captures: list[ArchiveCapture] = []
    for raw in payload[1 : _MAX_CAPTURES + 1]:
        if not isinstance(raw, list) or len(raw) != len(_FIELDS):
            raise AdapterExecutionError(
                "archive provider row shape changed",
                error_code="source_schema_drift",
                retryable=False,
            )
        try:
            captures.append(
                ArchiveCapture.model_validate(
                    {
                        key: int(value) if key == "length" else value
                        for key, value in zip(_FIELDS, raw, strict=True)
                    }
                )
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise AdapterExecutionError(
                "archive provider row is invalid",
                error_code="source_schema_drift",
                retryable=False,
            ) from exc
    return tuple(captures)


def _lead(
    capture: ArchiveCapture,
    *,
    target: PublicWebTarget,
    observed_at: datetime,
) -> ArchiveCaptureLead:
    capture_at = datetime.strptime(capture.timestamp, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
    capture_url = f"https://web.archive.org/web/{capture.timestamp}id_/{capture.original}"
    return ArchiveCaptureLead(
        organization_id=target.organization_id,
        source_id=InternetArchiveCdxAdapter.source_id,
        source_record_key=f"{capture.timestamp}:{capture.digest}",
        original_url=capture.original,
        capture_url=capture_url,
        capture_at=capture_at,
        observed_at=observed_at,
        archived_mime_type=capture.mimetype,
        archived_status_code=int(capture.statuscode),
        archived_length=capture.length,
        archived_digest=capture.digest,
    )


def _observation(
    capture: ArchiveCapture,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    source_url: str,
) -> RawObservation:
    encoded = capture.model_dump_json().encode("utf-8")
    return RawObservation(
        source_id=InternetArchiveCdxAdapter.source_id,
        adapter_id=InternetArchiveCdxAdapter.adapter_id,
        adapter_version=InternetArchiveCdxAdapter.adapter_version,
        collection_job_id=collection_job_id,
        source_record_type="internet-archive-cdx-capture",
        source_url=source_url,
        payload_hash_sha256=sha256(encoded).hexdigest(),
        data_categories=frozenset({DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}),
        source_record_key=f"{capture.timestamp}:{capture.digest}",
        collected_at=collected_at,
        retention_until=retention_until,
        schema_fingerprint="internet-archive-cdx:v1",
    )


def _next_target(
    targets: tuple[PublicWebTarget, ...],
    payload: Mapping[str, object] | None,
) -> tuple[PublicWebTarget | None, int]:
    if not targets:
        return None, 0
    value = 0 if payload is None else payload.get("target_index", 0)
    if not isinstance(value, int) or value < 0:
        raise AdapterExecutionError(
            "invalid archive checkpoint",
            error_code="invalid_checkpoint",
            retryable=False,
        )
    index = value % len(targets)
    return targets[index], 0 if index + 1 >= len(targets) else index + 1


def _empty_batch() -> AdapterCollectionBatch:
    return AdapterCollectionBatch(
        observations=(),
        public_footprint_projections=(),
        checkpoint_payload={"target_index": 0},
        not_modified=True,
    )

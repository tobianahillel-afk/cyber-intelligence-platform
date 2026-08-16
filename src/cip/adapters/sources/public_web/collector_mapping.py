from __future__ import annotations

from datetime import datetime
from uuid import UUID

from cip.adapters.sources.public_web.client import PublicWebFetchResult
from cip.adapters.sources.public_web.collection_policy import PublicWebCollectionDeniedError
from cip.adapters.sources.public_web.collector_state import (
    CURRENT_EXTRACTION_PROFILE,
    CollectionContext,
    PageCheckpoint,
    safe_validator,
)
from cip.adapters.sources.public_web.discovery import PublicWebDiscoveryCandidate
from cip.adapters.sources.public_web.mapper import (
    MappedPublicPage,
    PreviousPageState,
    map_public_page,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.adapters.sources.public_web.security_txt import parse_security_txt
from cip.adapters.sources.public_web.security_txt_mapper import map_security_txt


def apply_fetched(
    context: CollectionContext,
    candidate: PublicWebDiscoveryCandidate,
    previous: PageCheckpoint | None,
    fetched: PublicWebFetchResult,
) -> None:
    if candidate.security_txt and fetched.status_code in {404, 410}:
        return
    mapped = map_candidate(
        context.target,
        candidate,
        fetched,
        collection_job_id=context.collection_job_id,
        collected_at=context.collected_at,
        retention_until=context.retention_until,
        previous=previous,
        adapter_id=context.adapter_id,
    )
    if mapped.observation is not None:
        context.observations.append(mapped.observation)
    context.projections.append(mapped.projection)
    context.next_pages[candidate.url] = next_page_checkpoint(
        candidate,
        previous,
        mapped,
        fetched,
    )


def next_page_checkpoint(
    candidate: PublicWebDiscoveryCandidate,
    previous: PageCheckpoint | None,
    mapped: MappedPublicPage,
    fetched: PublicWebFetchResult,
) -> PageCheckpoint:
    not_modified = fetched.status_code == 304
    mime_type = (
        previous.mime_type
        if not_modified and previous is not None
        else fetched.mime_type
    )
    byte_size = (
        previous.byte_size
        if not_modified and previous is not None
        else len(fetched.body)
    )
    return PageCheckpoint(
        content_hash_sha256=mapped.content_hash_sha256,
        version_id=checkpoint_version_id(previous, mapped, fetched),
        canonical_url=fetched.fetched_url,
        resource_kind=mapped.projection.resource.kind,
        etag=safe_validator(fetched.etag),
        last_modified=safe_validator(fetched.last_modified),
        mime_type=mime_type,
        byte_size=byte_size,
        discovery_method=candidate.discovery_method,
        source_locator=candidate.source_locator,
        depth=candidate.depth,
        security_txt=candidate.security_txt,
        extraction_profile=CURRENT_EXTRACTION_PROFILE,
    )


def map_candidate(
    target: PublicWebTarget,
    candidate: PublicWebDiscoveryCandidate,
    fetched: PublicWebFetchResult,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    previous: PageCheckpoint | None,
    adapter_id: str,
) -> MappedPublicPage:
    previous_state = previous_state_from_checkpoint(previous)
    if candidate.security_txt:
        if fetched.mime_type != "text/plain":
            raise PublicWebCollectionDeniedError(
                "security.txt must be served as text/plain"
            )
        return map_security_txt(
            target,
            fetched,
            parse_security_txt(fetched.body, target),
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
            previous=previous_state,
        )
    return map_public_page(
        target,
        fetched,
        collection_job_id=collection_job_id,
        collected_at=collected_at,
        retention_until=retention_until,
        previous=previous_state,
        discovery_method=candidate.discovery_method,
        discovery_source_url=candidate.source_locator,
        allow_claims=True,
        adapter_id=adapter_id,
    )


def previous_state_from_checkpoint(
    previous: PageCheckpoint | None,
) -> PreviousPageState | None:
    if previous is None:
        return None
    return PreviousPageState(
        content_hash_sha256=previous.content_hash_sha256,
        version_id=previous.version_id,
        canonical_url=previous.canonical_url,
        resource_kind=previous.resource_kind,
        mime_type=previous.mime_type,
        byte_size=previous.byte_size,
    )


def checkpoint_version_id(
    previous: PageCheckpoint | None,
    mapped: MappedPublicPage,
    fetched: PublicWebFetchResult,
) -> UUID:
    unchanged = bool(
        previous is not None
        and previous.content_hash_sha256 == mapped.content_hash_sha256
        and previous.canonical_url == fetched.fetched_url
    )
    if unchanged and previous is not None:
        return previous.version_id
    return mapped.projection.version.id

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from uuid import UUID

from cip.adapters.sources.public_web.client import PublicWebFetchResult
from cip.adapters.sources.public_web.mapper import MappedPublicPage, PreviousPageState
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.adapters.sources.public_web.security_txt import (
    SecurityTxtDocument,
    bounded_security_txt_excerpt,
)
from cip.modules.public_footprint.domain.models import (
    DiscoveryMethod,
    PublicFootprintProjection,
    PublicResource,
    PublicResourceKind,
    PublicResourceVersion,
    ResourceAccessState,
    ResourceRetrievalState,
)
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import DataCategory


def map_security_txt(
    target: PublicWebTarget,
    result: PublicWebFetchResult,
    document: SecurityTxtDocument,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    previous: PreviousPageState | None,
) -> MappedPublicPage:
    content_hash = sha256(result.body).hexdigest()
    unchanged = bool(
        previous is not None
        and previous.content_hash_sha256 == content_hash
        and previous.canonical_url == result.fetched_url
    )
    excerpt = bounded_security_txt_excerpt(document)
    source_id = target.source_id or target.id
    resource = PublicResource(
        organization_id=target.organization_id,
        source_id=source_id,
        source_record_key=result.requested_url,
        canonical_url=result.fetched_url,
        source_url=result.requested_url,
        kind=PublicResourceKind.DOCUMENT,
        discovery_method=DiscoveryMethod.DIRECT,
        first_discovered_at=collected_at,
        last_seen_at=collected_at,
        access_state=ResourceAccessState.PUBLIC,
        retrieval_state=_retrieval_state(previous, unchanged=unchanged),
        title="security.txt",
    )
    version = PublicResourceVersion(
        resource_key=resource.identity_key,
        source_url=result.fetched_url,
        content_hash_sha256=content_hash,
        fetched_at=collected_at,
        mime_type=result.mime_type,
        byte_size=len(result.body),
        title="security.txt",
        extracted_text_hash_sha256=sha256(excerpt.encode()).hexdigest(),
        excerpt=excerpt,
        source_locator=result.fetched_url,
        supersedes_version_id=(
            previous.version_id
            if previous is not None
            and not unchanged
            and previous.canonical_url == result.fetched_url
            else None
        ),
    )
    projection = PublicFootprintProjection(resource=resource, version=version, claims=())
    observation = None
    if not unchanged:
        observation = RawObservation(
            source_id=source_id,
            adapter_id="public-web-sitemap",
            adapter_version="1",
            collection_job_id=collection_job_id,
            source_record_type="public_security_txt",
            source_record_key=result.requested_url,
            source_url=result.fetched_url,
            payload_hash_sha256=content_hash,
            data_categories=frozenset({DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}),
            collected_at=collected_at,
            observed_at=collected_at,
            source_updated_at=collected_at,
            schema_fingerprint="public-security-txt-v1",
            retention_until=retention_until,
        )
    return MappedPublicPage(
        projection=projection,
        observation=observation,
        content_hash_sha256=content_hash,
    )


def _retrieval_state(
    previous: PreviousPageState | None,
    *,
    unchanged: bool,
) -> ResourceRetrievalState:
    if unchanged:
        return ResourceRetrievalState.NOT_MODIFIED
    if previous is not None:
        return ResourceRetrievalState.CHANGED
    return ResourceRetrievalState.FETCHED

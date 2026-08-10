from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from uuid import UUID

from pydantic import BaseModel

from cip.modules.public_footprint.domain.models import (
    DiscoveryMethod,
    PublicFootprintProjection,
    PublicResource,
    PublicResourceKind,
    PublicResourceVersion,
    ResourceAccessState,
    ResourceRetrievalState,
)


@dataclass(frozen=True, slots=True)
class PublicMetadataResourceInput:
    organization_id: UUID
    source_id: str
    source_record_key: str
    canonical_url: str
    source_url: str
    kind: PublicResourceKind
    discovery_method: DiscoveryMethod
    collected_at: datetime
    title: str
    excerpt: str | None
    source_updated_at: datetime | None = None


def map_public_metadata_resource(
    model: BaseModel,
    metadata: PublicMetadataResourceInput,
) -> PublicFootprintProjection:
    encoded = model.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")
    content_hash = sha256(encoded).hexdigest()
    resource = PublicResource(
        organization_id=metadata.organization_id,
        source_id=metadata.source_id,
        source_record_key=metadata.source_record_key,
        canonical_url=metadata.canonical_url,
        source_url=metadata.source_url,
        kind=metadata.kind,
        discovery_method=metadata.discovery_method,
        first_discovered_at=metadata.collected_at,
        last_seen_at=metadata.collected_at,
        access_state=ResourceAccessState.PUBLIC,
        retrieval_state=ResourceRetrievalState.FETCHED,
        title=metadata.title,
    )
    version = PublicResourceVersion(
        resource_key=resource.identity_key,
        source_url=metadata.source_url,
        content_hash_sha256=content_hash,
        fetched_at=metadata.collected_at,
        mime_type="application/json",
        byte_size=len(encoded),
        source_updated_at=metadata.source_updated_at,
        title=metadata.title,
        excerpt=metadata.excerpt,
        source_locator=metadata.source_url,
    )
    return PublicFootprintProjection(resource=resource, version=version)

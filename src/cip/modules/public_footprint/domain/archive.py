from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from json import dumps
from uuid import UUID

from cip.modules.public_footprint.domain.models import (
    DiscoveryMethod,
    PublicFootprintProjection,
    PublicResource,
    PublicResourceKind,
    PublicResourceVersion,
    ResourceAccessState,
    ResourceRetrievalState,
)
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl
from cip.shared.kernel.time import require_aware_utc

_ARCHIVE_METADATA_MIME_TYPE = "application/x-archive-index-metadata"
_COMMON_CRAWL_METADATA_MIME_TYPE = "application/x-common-crawl-index-metadata"


@dataclass(frozen=True, slots=True)
class ArchiveCaptureLead:
    organization_id: UUID
    source_id: str
    source_record_key: str
    original_url: str
    capture_url: str
    capture_at: datetime
    observed_at: datetime
    archived_mime_type: str
    archived_status_code: int
    archived_length: int
    archived_digest: str

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.source_record_key.strip():
            raise ValueError("archive lead source identity is required")
        object.__setattr__(self, "original_url", CanonicalUrl(self.original_url).value)
        object.__setattr__(self, "capture_url", CanonicalUrl(self.capture_url).value)
        object.__setattr__(
            self,
            "capture_at",
            require_aware_utc(self.capture_at, field_name="capture_at"),
        )
        object.__setattr__(
            self,
            "observed_at",
            require_aware_utc(self.observed_at, field_name="observed_at"),
        )
        if not 100 <= self.archived_status_code <= 599:
            raise ValueError("archive status code is invalid")
        if self.archived_length < 0:
            raise ValueError("archive length cannot be negative")
        if not self.archived_mime_type.strip() or not self.archived_digest.strip():
            raise ValueError("archive mime type and digest are required")


@dataclass(frozen=True, slots=True)
class CommonCrawlIndexLead:
    organization_id: UUID
    source_id: str
    source_record_key: str
    original_url: str
    index_url: str
    crawl_id: str
    capture_at: datetime
    observed_at: datetime
    archived_mime_type: str
    archived_status_code: int
    archived_length: int
    archived_digest: str
    warc_filename: str
    warc_offset: int
    warc_record_length: int

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.source_record_key.strip():
            raise ValueError("Common Crawl lead source identity is required")
        if not self.crawl_id.startswith("CC-MAIN-"):
            raise ValueError("Common Crawl lead crawl identity is invalid")
        object.__setattr__(self, "original_url", CanonicalUrl(self.original_url).value)
        object.__setattr__(self, "index_url", CanonicalUrl(self.index_url).value)
        object.__setattr__(
            self,
            "capture_at",
            require_aware_utc(self.capture_at, field_name="capture_at"),
        )
        object.__setattr__(
            self,
            "observed_at",
            require_aware_utc(self.observed_at, field_name="observed_at"),
        )
        if not 100 <= self.archived_status_code <= 599:
            raise ValueError("Common Crawl status code is invalid")
        if min(self.archived_length, self.warc_offset, self.warc_record_length) < 0:
            raise ValueError("Common Crawl lengths and offset cannot be negative")
        required = (
            self.archived_mime_type,
            self.archived_digest,
            self.warc_filename,
        )
        if any(not value.strip() for value in required):
            raise ValueError("Common Crawl archive metadata is incomplete")


def map_archive_capture_lead(lead: ArchiveCaptureLead) -> PublicFootprintProjection:
    resource = PublicResource(
        organization_id=lead.organization_id,
        source_id=lead.source_id,
        source_record_key=lead.source_record_key,
        canonical_url=lead.original_url,
        source_url=lead.capture_url,
        kind=PublicResourceKind.ARCHIVE_SNAPSHOT,
        discovery_method=DiscoveryMethod.ARCHIVE_INDEX,
        first_discovered_at=lead.observed_at,
        last_seen_at=lead.observed_at,
        access_state=ResourceAccessState.UNKNOWN,
        retrieval_state=ResourceRetrievalState.QUARANTINED,
        title=f"Archived snapshot {lead.capture_at.isoformat()}",
    )
    material = _metadata_material(lead)
    version = PublicResourceVersion(
        resource_key=resource.identity_key,
        source_url=lead.capture_url,
        content_hash_sha256=sha256(material).hexdigest(),
        fetched_at=lead.observed_at,
        mime_type=_ARCHIVE_METADATA_MIME_TYPE,
        byte_size=len(material),
        title=resource.title,
        excerpt=(
            f"Historical archive index metadata: {lead.archived_mime_type}, "
            f"HTTP {lead.archived_status_code}."
        ),
        source_locator=f"archive-capture:{lead.capture_at.isoformat()}",
    )
    return PublicFootprintProjection(resource=resource, version=version, claims=())


def map_common_crawl_index_lead(lead: CommonCrawlIndexLead) -> PublicFootprintProjection:
    resource = PublicResource(
        organization_id=lead.organization_id,
        source_id=lead.source_id,
        source_record_key=lead.source_record_key,
        canonical_url=lead.original_url,
        source_url=lead.index_url,
        kind=PublicResourceKind.ARCHIVE_SNAPSHOT,
        discovery_method=DiscoveryMethod.ARCHIVE_INDEX,
        first_discovered_at=lead.observed_at,
        last_seen_at=lead.observed_at,
        access_state=ResourceAccessState.UNKNOWN,
        retrieval_state=ResourceRetrievalState.QUARANTINED,
        title=f"Common Crawl index capture {lead.capture_at.isoformat()}",
    )
    material = _common_crawl_metadata_material(lead)
    version = PublicResourceVersion(
        resource_key=resource.identity_key,
        source_url=lead.index_url,
        content_hash_sha256=sha256(material).hexdigest(),
        fetched_at=lead.observed_at,
        mime_type=_COMMON_CRAWL_METADATA_MIME_TYPE,
        byte_size=len(material),
        title=resource.title,
        excerpt=(
            f"Common Crawl index metadata from {lead.crawl_id}: "
            f"{lead.archived_mime_type}, HTTP {lead.archived_status_code}; "
            "WARC body not retrieved."
        ),
        source_locator=f"common-crawl:{lead.crawl_id}:{lead.capture_at.isoformat()}",
    )
    return PublicFootprintProjection(resource=resource, version=version, claims=())


def _metadata_material(lead: ArchiveCaptureLead) -> bytes:
    return dumps(
        {
            "archived_digest": lead.archived_digest,
            "archived_length": lead.archived_length,
            "archived_mime_type": lead.archived_mime_type,
            "archived_status_code": lead.archived_status_code,
            "capture_at": lead.capture_at.isoformat(),
            "capture_url": lead.capture_url,
            "original_url": lead.original_url,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _common_crawl_metadata_material(lead: CommonCrawlIndexLead) -> bytes:
    return dumps(
        {
            "archived_digest": lead.archived_digest,
            "archived_length": lead.archived_length,
            "archived_mime_type": lead.archived_mime_type,
            "archived_status_code": lead.archived_status_code,
            "capture_at": lead.capture_at.isoformat(),
            "crawl_id": lead.crawl_id,
            "index_url": lead.index_url,
            "original_url": lead.original_url,
            "warc_filename": lead.warc_filename,
            "warc_offset": lead.warc_offset,
            "warc_record_length": lead.warc_record_length,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
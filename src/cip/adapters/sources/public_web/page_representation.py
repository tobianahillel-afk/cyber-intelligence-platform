from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from uuid import UUID, uuid4

from cip.adapters.sources.public_web.client import (
    PublicWebFetchResult,
    PublicWebResponseError,
)
from cip.adapters.sources.public_web.content_extraction import ExtractedPublicContent
from cip.adapters.sources.public_web.ooxml_parsing import DOCX_MIME, PPTX_MIME, XLSX_MIME
from cip.modules.public_footprint.domain import (
    PublicResource,
    PublicResourceKind,
    PublicResourceVersion,
)

_TOMBSTONE_MIME_TYPE = "application/x-public-resource-tombstone"
_NOT_MODIFIED_STATUS = 304
_DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    DOCX_MIME,
    XLSX_MIME,
    PPTX_MIME,
}


@dataclass(frozen=True, slots=True)
class PreviousPageState:
    content_hash_sha256: str
    version_id: UUID
    canonical_url: str
    resource_kind: PublicResourceKind = PublicResourceKind.WEB_PAGE
    mime_type: str | None = None
    byte_size: int | None = None


@dataclass(frozen=True, slots=True)
class PageVersionContext:
    collected_at: datetime
    previous: PreviousPageState | None
    unchanged: bool
    not_modified: bool
    content_hash: str
    indexable_text: str
    extracted: ExtractedPublicContent | None
    tombstoned: bool
    discovery_source_url: str | None


def validate_not_modified(
    previous: PreviousPageState | None,
    result: PublicWebFetchResult,
) -> None:
    state = required_previous(previous)
    if state.canonical_url != result.fetched_url:
        raise PublicWebResponseError("304 response changed the canonical resource URL")
    if state.mime_type is None or state.byte_size is None:
        raise PublicWebResponseError(
            "304 response requires complete previous representation metadata"
        )


def content_hash(
    result: PublicWebFetchResult,
    previous: PreviousPageState | None,
) -> str:
    if result.status_code == _NOT_MODIFIED_STATUS:
        return required_previous(previous).content_hash_sha256
    if is_tombstone(result):
        return sha256(f"http-status:{result.status_code}".encode()).hexdigest()
    return sha256(result.body).hexdigest()


def resource_kind(
    result: PublicWebFetchResult,
    previous: PreviousPageState | None,
) -> PublicResourceKind:
    unchanged_or_tombstoned = (
        result.status_code == _NOT_MODIFIED_STATUS or is_tombstone(result)
    )
    if unchanged_or_tombstoned and previous is not None:
        return previous.resource_kind
    if result.mime_type in _DOCUMENT_MIME_TYPES:
        return PublicResourceKind.DOCUMENT
    return PublicResourceKind.WEB_PAGE


def build_version(
    resource: PublicResource,
    result: PublicWebFetchResult,
    context: PageVersionContext,
) -> PublicResourceVersion:
    previous = context.previous
    excerpt = (
        f"HTTP {result.status_code} tombstone"
        if context.tombstoned
        else context.extracted.excerpt if context.extracted is not None else None
    )
    mime_type = (
        required_previous(previous).mime_type
        if context.not_modified
        else result.mime_type
    )
    byte_size = (
        required_previous(previous).byte_size
        if context.not_modified
        else len(result.body)
    )
    assert mime_type is not None
    assert byte_size is not None
    return PublicResourceVersion(
        resource_key=resource.identity_key,
        source_url=result.fetched_url,
        content_hash_sha256=context.content_hash,
        fetched_at=context.collected_at,
        mime_type=mime_type,
        byte_size=byte_size,
        id=(
            required_previous(previous).version_id
            if context.not_modified
            else uuid4()
        ),
        published_at=(
            context.extracted.published_at if context.extracted is not None else None
        ),
        source_updated_at=(
            context.extracted.source_updated_at if context.extracted is not None else None
        ),
        title=(
            context.extracted.title if context.extracted is not None else None
        ),
        language=(
            context.extracted.language if context.extracted is not None else None
        ),
        extracted_text_hash_sha256=(
            sha256(context.indexable_text.encode()).hexdigest()
            if context.indexable_text
            else None
        ),
        excerpt=excerpt,
        source_locator=context.discovery_source_url or result.fetched_url,
        supersedes_version_id=predecessor_id(
            previous,
            result.fetched_url,
            unchanged=context.unchanged,
        ),
    )


def is_tombstone(result: PublicWebFetchResult) -> bool:
    return result.status_code in {404, 410} and result.mime_type == _TOMBSTONE_MIME_TYPE


def required_previous(previous: PreviousPageState | None) -> PreviousPageState:
    if previous is None:
        raise PublicWebResponseError("304 response requires previous page state")
    return previous


def predecessor_id(
    previous: PreviousPageState | None,
    canonical_url: str,
    *,
    unchanged: bool,
) -> UUID | None:
    if previous is None or unchanged or previous.canonical_url != canonical_url:
        return None
    return previous.version_id

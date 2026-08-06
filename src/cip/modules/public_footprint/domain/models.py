from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from uuid import UUID, uuid4

from cip.modules.public_footprint.domain.url_identity import CanonicalUrl
from cip.shared.kernel.time import require_aware_utc


class PublicResourceKind(StrEnum):
    SITEMAP = "sitemap"
    FEED = "feed"
    STRUCTURED_DATA = "structured_data"
    WEB_PAGE = "web_page"
    DOCUMENT = "document"
    REPOSITORY = "repository"
    ARCHIVE_SNAPSHOT = "archive_snapshot"
    SEARCH_RESULT = "search_result"


class DiscoveryMethod(StrEnum):
    DIRECT = "direct"
    SITEMAP = "sitemap"
    FEED = "feed"
    LINK = "link"
    STRUCTURED_DATA = "structured_data"
    SEARCH_API = "search_api"
    ANALYST_LINK = "analyst_link"
    ARCHIVE_INDEX = "archive_index"
    REPOSITORY_API = "repository_api"


class ResourceAccessState(StrEnum):
    PUBLIC = "public"
    UNKNOWN = "unknown"
    RESTRICTED = "restricted"


class ResourceRetrievalState(StrEnum):
    DISCOVERED = "discovered"
    FETCHED = "fetched"
    NOT_MODIFIED = "not_modified"
    CHANGED = "changed"
    TOMBSTONED = "tombstoned"
    QUARANTINED = "quarantined"


class PublicClaimType(StrEnum):
    CONTRACT_OR_PROJECT = "contract_or_project"
    TECHNOLOGY_OR_ARCHITECTURE = "technology_or_architecture"
    PROVIDER_PARTNER_CUSTOMER = "provider_partner_customer"
    SECURITY_OR_COMPLIANCE_OBJECTIVE = "security_or_compliance_objective"
    PROFESSIONAL_CONTACT_PATH = "professional_contact_path"
    CORPORATE_CHANGE = "corporate_change"


class ClaimEvidenceBasis(StrEnum):
    SEARCH_RESULT_METADATA = "search_result_metadata"
    TARGET_CONTENT = "target_content"
    STRUCTURED_DATA = "structured_data"
    ARCHIVE_CONTENT = "archive_content"
    REPOSITORY_METADATA = "repository_metadata"
    FEED_ENTRY = "feed_entry"


class ClaimResolutionStatus(StrEnum):
    OBSERVED = "observed"
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    CONTRADICTED = "contradicted"
    RETRACTED = "retracted"


@dataclass(frozen=True, slots=True)
class PublicResource:
    organization_id: UUID
    source_id: str
    source_record_key: str
    canonical_url: str
    source_url: str
    kind: PublicResourceKind
    discovery_method: DiscoveryMethod
    first_discovered_at: datetime
    last_seen_at: datetime
    access_state: ResourceAccessState = ResourceAccessState.PUBLIC
    retrieval_state: ResourceRetrievalState = ResourceRetrievalState.DISCOVERED
    title: str | None = None

    def __post_init__(self) -> None:
        source_id = self.source_id.strip()
        record_key = self.source_record_key.strip()
        if not source_id or not record_key:
            raise ValueError("source_id and source_record_key are required")
        canonical_url = CanonicalUrl(self.canonical_url).value
        source_url = CanonicalUrl(self.source_url).value
        first_discovered = require_aware_utc(
            self.first_discovered_at,
            field_name="first_discovered_at",
        )
        last_seen = require_aware_utc(self.last_seen_at, field_name="last_seen_at")
        if last_seen < first_discovered:
            raise ValueError("last_seen_at cannot precede first_discovered_at")
        fetched_states = {
            ResourceRetrievalState.FETCHED,
            ResourceRetrievalState.NOT_MODIFIED,
            ResourceRetrievalState.CHANGED,
        }
        if (
            self.access_state is not ResourceAccessState.PUBLIC
            and self.retrieval_state in fetched_states
        ):
            raise ValueError("non-public resources cannot be marked as fetched")
        title = _optional_text(self.title, max_length=1_000, field_name="title")
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "source_record_key", record_key)
        object.__setattr__(self, "canonical_url", canonical_url)
        object.__setattr__(self, "source_url", source_url)
        object.__setattr__(self, "first_discovered_at", first_discovered)
        object.__setattr__(self, "last_seen_at", last_seen)
        object.__setattr__(self, "title", title)

    @property
    def identity_key(self) -> str:
        material = (
            f"{self.organization_id}\0{self.kind.value}\0{self.canonical_url}"
        )
        return sha256(material.encode("utf-8")).hexdigest()

    @property
    def corroboration_group_key(self) -> str:
        material = f"{self.organization_id}\0{self.canonical_url}"
        return sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PublicResourceVersion:
    resource_key: str
    source_url: str
    content_hash_sha256: str
    fetched_at: datetime
    mime_type: str
    byte_size: int
    id: UUID = field(default_factory=uuid4)
    published_at: datetime | None = None
    source_updated_at: datetime | None = None
    title: str | None = None
    language: str | None = None
    extracted_text_hash_sha256: str | None = None
    excerpt: str | None = None
    source_locator: str | None = None
    supersedes_version_id: UUID | None = None

    def __post_init__(self) -> None:
        resource_key = _required_hash(self.resource_key, field_name="resource_key")
        source_url = CanonicalUrl(self.source_url).value
        content_hash = _required_hash(
            self.content_hash_sha256,
            field_name="content_hash_sha256",
        )
        extracted_hash = _optional_hash(
            self.extracted_text_hash_sha256,
            field_name="extracted_text_hash_sha256",
        )
        fetched_at = require_aware_utc(self.fetched_at, field_name="fetched_at")
        published_at = _optional_time(self.published_at, field_name="published_at")
        source_updated_at = _optional_time(
            self.source_updated_at,
            field_name="source_updated_at",
        )
        mime_type = _normalize_mime_type(self.mime_type)
        if self.byte_size < 0:
            raise ValueError("byte_size cannot be negative")
        title = _optional_text(self.title, max_length=1_000, field_name="title")
        language = _optional_text(self.language, max_length=35, field_name="language")
        excerpt = _optional_text(self.excerpt, max_length=1_000, field_name="excerpt")
        locator = _optional_text(
            self.source_locator,
            max_length=500,
            field_name="source_locator",
        )
        object.__setattr__(self, "resource_key", resource_key)
        object.__setattr__(self, "source_url", source_url)
        object.__setattr__(self, "content_hash_sha256", content_hash)
        object.__setattr__(self, "extracted_text_hash_sha256", extracted_hash)
        object.__setattr__(self, "fetched_at", fetched_at)
        object.__setattr__(self, "published_at", published_at)
        object.__setattr__(self, "source_updated_at", source_updated_at)
        object.__setattr__(self, "mime_type", mime_type)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "language", language)
        object.__setattr__(self, "excerpt", excerpt)
        object.__setattr__(self, "source_locator", locator)

    @property
    def version_key(self) -> str:
        material = f"{self.resource_key}\0{self.content_hash_sha256}"
        return sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PublicClaim:
    organization_id: UUID
    resource_version_id: UUID
    claim_type: PublicClaimType
    statement: str
    evidence_basis: ClaimEvidenceBasis
    resolution_status: ClaimResolutionStatus
    confidence: float
    corroboration_group_key: str
    source_locator: str | None = None
    excerpt: str | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        statement = _required_text(
            self.statement,
            max_length=2_000,
            field_name="statement",
        )
        group_key = _required_hash(
            self.corroboration_group_key,
            field_name="corroboration_group_key",
        )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("claim confidence must be between 0 and 1")
        if (
            self.evidence_basis is ClaimEvidenceBasis.SEARCH_RESULT_METADATA
            and self.resolution_status is ClaimResolutionStatus.CONFIRMED
        ):
            raise ValueError("search-result metadata cannot confirm a claim")
        locator = _optional_text(
            self.source_locator,
            max_length=500,
            field_name="source_locator",
        )
        excerpt = _optional_text(self.excerpt, max_length=1_000, field_name="excerpt")
        object.__setattr__(self, "statement", statement)
        object.__setattr__(self, "corroboration_group_key", group_key)
        object.__setattr__(self, "source_locator", locator)
        object.__setattr__(self, "excerpt", excerpt)

    @property
    def identity_key(self) -> str:
        normalized_statement = " ".join(self.statement.casefold().split())
        material = (
            f"{self.organization_id}\0{self.claim_type.value}\0"
            f"{normalized_statement}\0{self.corroboration_group_key}"
        )
        return sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PublicFootprintProjection:
    resource: PublicResource
    version: PublicResourceVersion
    claims: tuple[PublicClaim, ...] = ()

    def __post_init__(self) -> None:
        if self.version.resource_key != self.resource.identity_key:
            raise ValueError("resource version must match projected resource")
        unique_claims: dict[str, PublicClaim] = {}
        for claim in self.claims:
            if claim.organization_id != self.resource.organization_id:
                raise ValueError("claim organization must match projected resource")
            if claim.resource_version_id != self.version.id:
                raise ValueError("claim version must match projected resource version")
            if claim.corroboration_group_key != self.resource.corroboration_group_key:
                raise ValueError("claim corroboration group must match resource target")
            unique_claims[claim.identity_key] = claim
        object.__setattr__(self, "claims", tuple(unique_claims.values()))


def _required_hash(value: str, *, field_name: str) -> str:
    normalized = value.strip().casefold()
    if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return normalized


def _optional_hash(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_hash(value, field_name=field_name)


def _required_text(value: str, *, max_length: int, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} cannot exceed {max_length} characters")
    return normalized


def _optional_text(
    value: str | None,
    *,
    max_length: int,
    field_name: str,
) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} cannot exceed {max_length} characters")
    return normalized


def _optional_time(value: datetime | None, *, field_name: str) -> datetime | None:
    if value is None:
        return None
    return require_aware_utc(value, field_name=field_name)


def _normalize_mime_type(value: str) -> str:
    mime_type = value.split(";", 1)[0].strip().casefold()
    if "/" not in mime_type:
        raise ValueError("mime_type must contain a type and subtype")
    return mime_type

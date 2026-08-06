from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from json import dumps
from uuid import UUID

from cip.modules.public_footprint.domain.models import (
    ClaimEvidenceBasis,
    ClaimResolutionStatus,
    DiscoveryMethod,
    PublicClaim,
    PublicClaimType,
    PublicFootprintProjection,
    PublicResource,
    PublicResourceKind,
    PublicResourceVersion,
    ResourceAccessState,
    ResourceRetrievalState,
)
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl
from cip.shared.kernel.time import require_aware_utc

_SEARCH_RESULT_MIME_TYPE = "application/x-search-result-metadata"


@dataclass(frozen=True, slots=True)
class SearchQueryTemplate:
    id: str
    version: int
    query_pattern: str
    purpose: str
    enabled: bool = False

    def __post_init__(self) -> None:
        identifier = _required_text(self.id, field_name="id", max_length=100)
        pattern = _required_text(
            self.query_pattern,
            field_name="query_pattern",
            max_length=500,
        )
        purpose = _required_text(self.purpose, field_name="purpose", max_length=200)
        if self.version < 1:
            raise ValueError("search query template version must be positive")
        if pattern.count("{organization}") != 1:
            raise ValueError("search query pattern requires one {organization} placeholder")
        object.__setattr__(self, "id", identifier)
        object.__setattr__(self, "query_pattern", pattern)
        object.__setattr__(self, "purpose", purpose)

    def render(self, organization_name: str) -> str:
        name = _required_text(
            organization_name,
            field_name="organization_name",
            max_length=300,
        )
        return self.query_pattern.replace("{organization}", name)


@dataclass(frozen=True, slots=True)
class SearchLeadClaim:
    claim_type: PublicClaimType
    statement: str
    confidence: float

    def __post_init__(self) -> None:
        statement = _required_text(
            self.statement,
            field_name="statement",
            max_length=2_000,
        )
        if not 0.0 <= self.confidence <= 0.5:
            raise ValueError("search lead confidence must be between 0 and 0.5")
        object.__setattr__(self, "statement", statement)


@dataclass(frozen=True, slots=True)
class SearchResultLead:
    organization_id: UUID
    source_id: str
    source_record_key: str
    target_url: str
    title: str
    snippet: str
    rank: int
    observed_at: datetime
    query_template_id: str
    query_template_version: int
    candidate_claim: SearchLeadClaim | None = None

    def __post_init__(self) -> None:
        source_id = _required_text(self.source_id, field_name="source_id", max_length=100)
        record_key = _required_text(
            self.source_record_key,
            field_name="source_record_key",
            max_length=500,
        )
        target_url = CanonicalUrl(self.target_url).value
        title = _required_text(self.title, field_name="title", max_length=1_000)
        snippet = _required_text(self.snippet, field_name="snippet", max_length=1_000)
        template_id = _required_text(
            self.query_template_id,
            field_name="query_template_id",
            max_length=100,
        )
        observed_at = require_aware_utc(self.observed_at, field_name="observed_at")
        if self.rank < 1 or self.rank > 1_000:
            raise ValueError("search result rank must be between 1 and 1000")
        if self.query_template_version < 1:
            raise ValueError("search query template version must be positive")
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "source_record_key", record_key)
        object.__setattr__(self, "target_url", target_url)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "snippet", snippet)
        object.__setattr__(self, "query_template_id", template_id)
        object.__setattr__(self, "observed_at", observed_at)


def map_search_result_lead(lead: SearchResultLead) -> PublicFootprintProjection:
    resource = PublicResource(
        organization_id=lead.organization_id,
        source_id=lead.source_id,
        source_record_key=lead.source_record_key,
        canonical_url=lead.target_url,
        source_url=lead.target_url,
        kind=PublicResourceKind.SEARCH_RESULT,
        discovery_method=DiscoveryMethod.SEARCH_API,
        first_discovered_at=lead.observed_at,
        last_seen_at=lead.observed_at,
        access_state=ResourceAccessState.UNKNOWN,
        retrieval_state=ResourceRetrievalState.QUARANTINED,
        title=lead.title,
    )
    material = _metadata_material(lead)
    version = PublicResourceVersion(
        resource_key=resource.identity_key,
        source_url=lead.target_url,
        content_hash_sha256=sha256(material).hexdigest(),
        fetched_at=lead.observed_at,
        mime_type=_SEARCH_RESULT_MIME_TYPE,
        byte_size=len(material),
        title=lead.title,
        excerpt=lead.snippet,
        source_locator=f"search-rank:{lead.rank}",
    )
    claims = _candidate_claims(lead, resource, version)
    return PublicFootprintProjection(resource=resource, version=version, claims=claims)


def _candidate_claims(
    lead: SearchResultLead,
    resource: PublicResource,
    version: PublicResourceVersion,
) -> tuple[PublicClaim, ...]:
    candidate = lead.candidate_claim
    if candidate is None:
        return ()
    return (
        PublicClaim(
            organization_id=lead.organization_id,
            resource_version_id=version.id,
            claim_type=candidate.claim_type,
            statement=candidate.statement,
            evidence_basis=ClaimEvidenceBasis.SEARCH_RESULT_METADATA,
            resolution_status=ClaimResolutionStatus.CANDIDATE,
            confidence=candidate.confidence,
            corroboration_group_key=resource.corroboration_group_key,
            source_locator=f"search-rank:{lead.rank}",
            excerpt=lead.snippet,
        ),
    )


def _metadata_material(lead: SearchResultLead) -> bytes:
    return dumps(
        {
            "query_template_id": lead.query_template_id,
            "query_template_version": lead.query_template_version,
            "rank": lead.rank,
            "snippet": lead.snippet,
            "target_url": lead.target_url,
            "title": lead.title,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _required_text(value: str, *, field_name: str, max_length: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} cannot exceed {max_length} characters")
    return normalized

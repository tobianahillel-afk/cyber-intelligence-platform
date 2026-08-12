from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from uuid import UUID

from cip.adapters.sources.public_web.client import PublicWebFetchResult
from cip.adapters.sources.public_web.content_extraction import (
    ExtractedPublicContent,
    extract_public_content,
)
from cip.adapters.sources.public_web.parsing import contains_credential_marker
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain import (
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
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import DataCategory

_TOMBSTONE_MIME_TYPE = "application/x-public-resource-tombstone"
_TECHNOLOGY_TERMS = (
    "amazon web services",
    "aws",
    "azure",
    "crowdstrike",
    "google cloud",
    "kubernetes",
    "microsoft sentinel",
    "okta",
    "palo alto networks",
    "splunk",
)
_SECURITY_OBJECTIVE_TERMS = (
    "cyber resilience",
    "incident response",
    "iso 27001",
    "nist cybersecurity framework",
    "ransomware preparedness",
    "soc 2",
    "zero trust",
)


@dataclass(frozen=True, slots=True)
class PreviousPageState:
    content_hash_sha256: str
    version_id: UUID
    canonical_url: str
    resource_kind: PublicResourceKind = PublicResourceKind.WEB_PAGE


@dataclass(frozen=True, slots=True)
class MappedPublicPage:
    projection: PublicFootprintProjection
    observation: RawObservation | None
    content_hash_sha256: str


def map_public_page(
    target: PublicWebTarget,
    result: PublicWebFetchResult,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    previous: PreviousPageState | None,
    discovery_method: DiscoveryMethod = DiscoveryMethod.SITEMAP,
    discovery_source_url: str | None = None,
    allow_claims: bool = True,
) -> MappedPublicPage:
    tombstoned = _is_tombstone(result)
    content_hash = _content_hash(result)
    quarantined = not tombstoned and contains_credential_marker(result.body)
    unchanged = _is_unchanged(previous, result, content_hash)
    extracted = extract_public_content(
        result,
        quarantined=quarantined,
        tombstoned=tombstoned,
    )
    indexable_text = _indexable_text(extracted)
    resource = _resource(
        target,
        result,
        collected_at=collected_at,
        previous=previous,
        quarantined=quarantined,
        tombstoned=tombstoned,
        unchanged=unchanged,
        extracted=extracted,
        discovery_method=discovery_method,
        discovery_source_url=discovery_source_url,
    )
    version = _version(
        resource,
        result,
        collected_at=collected_at,
        previous=previous,
        unchanged=unchanged,
        content_hash=content_hash,
        indexable_text=indexable_text,
        extracted=extracted,
        tombstoned=tombstoned,
    )
    claims = (
        ()
        if tombstoned or not allow_claims
        else _claims(target, resource, version, indexable_text)
    )
    projection = PublicFootprintProjection(resource=resource, version=version, claims=claims)
    observation = (
        None
        if unchanged
        else _observation(
            target,
            result,
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
            content_hash=content_hash,
            extracted=extracted,
            tombstoned=tombstoned,
            include_technology_category=allow_claims,
        )
    )
    return MappedPublicPage(
        projection=projection,
        observation=observation,
        content_hash_sha256=content_hash,
    )


def _resource(
    target: PublicWebTarget,
    result: PublicWebFetchResult,
    *,
    collected_at: datetime,
    previous: PreviousPageState | None,
    quarantined: bool,
    tombstoned: bool,
    unchanged: bool,
    extracted: ExtractedPublicContent | None,
    discovery_method: DiscoveryMethod,
    discovery_source_url: str | None,
) -> PublicResource:
    kind = _resource_kind(result, previous)
    return PublicResource(
        organization_id=target.organization_id,
        source_id=target.source_id or target.id,
        source_record_key=result.requested_url,
        canonical_url=result.fetched_url,
        source_url=discovery_source_url or result.requested_url,
        kind=kind,
        discovery_method=discovery_method,
        first_discovered_at=collected_at,
        last_seen_at=collected_at,
        access_state=(
            ResourceAccessState.UNKNOWN
            if quarantined or tombstoned
            else ResourceAccessState.PUBLIC
        ),
        retrieval_state=_retrieval_state(
            quarantined=quarantined,
            tombstoned=tombstoned,
            unchanged=unchanged,
            previous=previous,
        ),
        title=extracted.title if extracted is not None else None,
    )


def _version(
    resource: PublicResource,
    result: PublicWebFetchResult,
    *,
    collected_at: datetime,
    previous: PreviousPageState | None,
    unchanged: bool,
    content_hash: str,
    indexable_text: str,
    extracted: ExtractedPublicContent | None,
    tombstoned: bool,
) -> PublicResourceVersion:
    excerpt = (
        f"HTTP {result.status_code} tombstone"
        if tombstoned
        else extracted.excerpt if extracted is not None else None
    )
    return PublicResourceVersion(
        resource_key=resource.identity_key,
        source_url=result.fetched_url,
        content_hash_sha256=content_hash,
        fetched_at=collected_at,
        mime_type=result.mime_type,
        byte_size=len(result.body),
        title=extracted.title if extracted is not None else None,
        language=extracted.language if extracted is not None else None,
        extracted_text_hash_sha256=(
            sha256(indexable_text.encode()).hexdigest()
            if indexable_text
            else None
        ),
        excerpt=excerpt,
        source_locator=result.fetched_url,
        supersedes_version_id=_predecessor_id(
            previous,
            result.fetched_url,
            unchanged=unchanged,
        ),
    )


def _observation(
    target: PublicWebTarget,
    result: PublicWebFetchResult,
    *,
    collection_job_id: UUID,
    collected_at: datetime,
    retention_until: datetime,
    content_hash: str,
    extracted: ExtractedPublicContent | None,
    tombstoned: bool,
    include_technology_category: bool,
) -> RawObservation:
    categories = {DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}
    if not tombstoned and include_technology_category:
        categories.add(DataCategory.TECHNOLOGY_OBSERVATION)
    return RawObservation(
        source_id=target.source_id or target.id,
        adapter_id="public-web-sitemap",
        adapter_version="1",
        collection_job_id=collection_job_id,
        source_record_type=(
            "public_web_tombstone" if tombstoned else "public_web_resource"
        ),
        source_record_key=result.requested_url,
        source_url=result.fetched_url,
        payload_hash_sha256=content_hash,
        data_categories=frozenset(categories),
        collected_at=collected_at,
        observed_at=collected_at,
        source_updated_at=collected_at,
        schema_fingerprint=(
            "public-web-tombstone-v1" if tombstoned else "public-web-page-v1"
        ),
        content_language=extracted.language if extracted is not None else None,
        retention_until=retention_until,
    )


def _content_hash(result: PublicWebFetchResult) -> str:
    if _is_tombstone(result):
        return sha256(f"http-status:{result.status_code}".encode()).hexdigest()
    return sha256(result.body).hexdigest()


def _is_tombstone(result: PublicWebFetchResult) -> bool:
    return result.status_code in {404, 410} and result.mime_type == _TOMBSTONE_MIME_TYPE


def _is_unchanged(
    previous: PreviousPageState | None,
    result: PublicWebFetchResult,
    content_hash: str,
) -> bool:
    return bool(
        previous is not None
        and previous.content_hash_sha256 == content_hash
        and previous.canonical_url == result.fetched_url
    )


def _indexable_text(extracted: ExtractedPublicContent | None) -> str:
    if extracted is None or extracted.noindex:
        return ""
    return extracted.text


def _resource_kind(
    result: PublicWebFetchResult,
    previous: PreviousPageState | None,
) -> PublicResourceKind:
    if _is_tombstone(result) and previous is not None:
        return previous.resource_kind
    if result.mime_type in {"application/pdf", "text/plain"}:
        return PublicResourceKind.DOCUMENT
    return PublicResourceKind.WEB_PAGE


def _predecessor_id(
    previous: PreviousPageState | None,
    canonical_url: str,
    *,
    unchanged: bool,
) -> UUID | None:
    if previous is None or unchanged or previous.canonical_url != canonical_url:
        return None
    return previous.version_id


def _retrieval_state(
    *,
    quarantined: bool,
    tombstoned: bool,
    unchanged: bool,
    previous: PreviousPageState | None,
) -> ResourceRetrievalState:
    if quarantined:
        return ResourceRetrievalState.QUARANTINED
    if tombstoned:
        return ResourceRetrievalState.TOMBSTONED
    if unchanged:
        return ResourceRetrievalState.NOT_MODIFIED
    if previous is not None:
        return ResourceRetrievalState.CHANGED
    return ResourceRetrievalState.FETCHED


def _claims(
    target: PublicWebTarget,
    resource: PublicResource,
    version: PublicResourceVersion,
    text: str,
) -> tuple[PublicClaim, ...]:
    normalized = text.casefold()
    claims: list[PublicClaim] = []
    for term in _TECHNOLOGY_TERMS:
        if term in normalized:
            claims.append(
                _claim(
                    target,
                    resource,
                    version,
                    PublicClaimType.TECHNOLOGY_OR_ARCHITECTURE,
                    f"{target.canonical_name} publicly mentions {term}.",
                    term,
                )
            )
    for term in _SECURITY_OBJECTIVE_TERMS:
        if term in normalized:
            claims.append(
                _claim(
                    target,
                    resource,
                    version,
                    PublicClaimType.SECURITY_OR_COMPLIANCE_OBJECTIVE,
                    f"{target.canonical_name} publicly mentions {term}.",
                    term,
                )
            )
    return tuple(claims)


def _claim(
    target: PublicWebTarget,
    resource: PublicResource,
    version: PublicResourceVersion,
    claim_type: PublicClaimType,
    statement: str,
    matched_term: str,
) -> PublicClaim:
    return PublicClaim(
        organization_id=target.organization_id,
        resource_version_id=version.id,
        claim_type=claim_type,
        statement=statement,
        evidence_basis=ClaimEvidenceBasis.TARGET_CONTENT,
        resolution_status=ClaimResolutionStatus.OBSERVED,
        confidence=1.0,
        corroboration_group_key=resource.corroboration_group_key,
        source_locator=resource.canonical_url,
        excerpt=matched_term,
    )

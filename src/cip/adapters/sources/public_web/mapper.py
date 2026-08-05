from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from uuid import UUID

from cip.adapters.sources.public_web.client import PublicWebFetchResult
from cip.adapters.sources.public_web.parsing import (
    contains_credential_marker,
    extract_html,
)
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
) -> MappedPublicPage:
    content_hash = sha256(result.body).hexdigest()
    quarantined = contains_credential_marker(result.body)
    unchanged = bool(
        previous is not None
        and previous.content_hash_sha256 == content_hash
        and previous.canonical_url == result.fetched_url
    )
    retrieval_state = _retrieval_state(
        quarantined=quarantined,
        unchanged=unchanged,
        previous=previous,
    )
    extracted = (
        extract_html(result.body)
        if result.mime_type == "text/html" and not quarantined
        else None
    )
    indexable_text = (
        extracted.text if extracted is not None and not extracted.noindex else ""
    )
    resource = PublicResource(
        organization_id=target.organization_id,
        source_id=target.id,
        source_record_key=result.requested_url,
        canonical_url=result.fetched_url,
        source_url=result.requested_url,
        kind=(
            PublicResourceKind.DOCUMENT
            if result.mime_type == "application/pdf"
            else PublicResourceKind.WEB_PAGE
        ),
        discovery_method=DiscoveryMethod.SITEMAP,
        first_discovered_at=collected_at,
        last_seen_at=collected_at,
        access_state=(
            ResourceAccessState.UNKNOWN if quarantined else ResourceAccessState.PUBLIC
        ),
        retrieval_state=retrieval_state,
        title=extracted.title if extracted is not None else None,
    )
    version = PublicResourceVersion(
        resource_key=resource.identity_key,
        source_url=result.fetched_url,
        content_hash_sha256=content_hash,
        fetched_at=collected_at,
        mime_type=result.mime_type,
        byte_size=len(result.body),
        title=extracted.title if extracted is not None else None,
        language=extracted.language if extracted is not None else None,
        extracted_text_hash_sha256=(
            sha256(indexable_text.encode("utf-8")).hexdigest()
            if indexable_text
            else None
        ),
        excerpt=extracted.excerpt if extracted is not None else None,
        source_locator=result.fetched_url,
        supersedes_version_id=_predecessor_id(
            previous,
            result.fetched_url,
            unchanged=unchanged,
        ),
    )
    claims = _claims(target, resource, version, indexable_text)
    projection = PublicFootprintProjection(
        resource=resource,
        version=version,
        claims=claims,
    )
    observation = None
    if not unchanged:
        observation = RawObservation(
            source_id=target.id,
            adapter_id="public-web-sitemap",
            adapter_version="1",
            collection_job_id=collection_job_id,
            source_record_type="public_web_resource",
            source_record_key=result.requested_url,
            source_url=result.fetched_url,
            payload_hash_sha256=content_hash,
            data_categories=frozenset(
                {
                    DataCategory.OFFICIAL_DOCUMENT_DISCOVERY,
                    DataCategory.TECHNOLOGY_OBSERVATION,
                }
            ),
            collected_at=collected_at,
            observed_at=collected_at,
            source_updated_at=collected_at,
            schema_fingerprint="public-web-page-v1",
            content_language=extracted.language if extracted is not None else None,
            retention_until=retention_until,
        )
    return MappedPublicPage(
        projection=projection,
        observation=observation,
        content_hash_sha256=content_hash,
    )


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
    unchanged: bool,
    previous: PreviousPageState | None,
) -> ResourceRetrievalState:
    if quarantined:
        return ResourceRetrievalState.QUARANTINED
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

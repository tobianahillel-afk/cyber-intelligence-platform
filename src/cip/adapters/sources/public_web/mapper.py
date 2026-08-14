from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from cip.adapters.sources.public_web.client import PublicWebFetchResult
from cip.adapters.sources.public_web.content_extraction import (
    ExtractedPublicContent,
    extract_public_content,
)
from cip.adapters.sources.public_web.page_representation import (
    PageVersionContext,
    PreviousPageState,
    build_version,
    content_hash,
    is_tombstone,
    resource_kind,
    validate_not_modified,
)
from cip.adapters.sources.public_web.parsing import contains_credential_marker
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.adapters.sources.public_web.structured_state_mapping import map_structured_states
from cip.adapters.sources.public_web.surface_extraction import (
    extract_public_surface_references,
)
from cip.modules.public_footprint.domain import (
    ClaimEvidenceBasis,
    ClaimResolutionStatus,
    DiscoveryMethod,
    PublicClaim,
    PublicClaimType,
    PublicFootprintProjection,
    PublicResource,
    PublicResourceVersion,
    ResourceAccessState,
    ResourceRetrievalState,
)
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import DataCategory

__all__ = ("MappedPublicPage", "PreviousPageState", "map_public_page")

_NOT_MODIFIED_STATUS = 304
_DEFAULT_ADAPTER_ID = "public-web-sitemap"
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
    adapter_id: str = _DEFAULT_ADAPTER_ID,
) -> MappedPublicPage:
    not_modified = result.status_code == _NOT_MODIFIED_STATUS
    if not_modified:
        validate_not_modified(previous, result)
    tombstoned = is_tombstone(result)
    page_hash = content_hash(result, previous)
    quarantined = (
        not tombstoned
        and not not_modified
        and contains_credential_marker(result.body)
    )
    unchanged = not_modified or _is_unchanged(previous, result, page_hash)
    extracted = (
        None
        if not_modified
        else extract_public_content(
            result,
            quarantined=quarantined,
            tombstoned=tombstoned,
        )
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
    version = build_version(
        resource,
        result,
        PageVersionContext(
            collected_at=collected_at,
            previous=previous,
            unchanged=unchanged,
            not_modified=not_modified,
            content_hash=page_hash,
            indexable_text=indexable_text,
            extracted=extracted,
            tombstoned=tombstoned,
            discovery_source_url=discovery_source_url,
        ),
    )
    claims = (
        ()
        if tombstoned or not_modified or not allow_claims
        else _claims(target, resource, version, extracted)
    )
    surfaces = (
        ()
        if tombstoned or unchanged or quarantined
        else extract_public_surface_references(
            result,
            organization_id=target.organization_id,
            resource_version_id=version.id,
        )
    )
    structured_states = (
        ()
        if tombstoned or unchanged or quarantined
        else map_structured_states(
            result,
            organization_id=target.organization_id,
            resource_version_id=version.id,
        )
    )
    projection = PublicFootprintProjection(
        resource=resource,
        version=version,
        claims=claims,
        surfaces=surfaces,
        structured_states=structured_states,
    )
    observation = (
        None
        if unchanged
        else _observation(
            target,
            result,
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
            content_hash=page_hash,
            extracted=extracted,
            tombstoned=tombstoned,
            include_technology_category=allow_claims,
            adapter_id=adapter_id,
        )
    )
    return MappedPublicPage(
        projection=projection,
        observation=observation,
        content_hash_sha256=page_hash,
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
    return PublicResource(
        organization_id=target.organization_id,
        source_id=target.source_id or target.id,
        source_record_key=result.requested_url,
        canonical_url=result.fetched_url,
        source_url=discovery_source_url or result.requested_url,
        kind=resource_kind(result, previous),
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
    adapter_id: str,
) -> RawObservation:
    categories = {DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}
    if not tombstoned and include_technology_category:
        categories.add(DataCategory.TECHNOLOGY_OBSERVATION)
    return RawObservation(
        source_id=target.source_id or target.id,
        adapter_id=adapter_id,
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


def _is_unchanged(
    previous: PreviousPageState | None,
    result: PublicWebFetchResult,
    page_hash: str,
) -> bool:
    return bool(
        previous is not None
        and previous.content_hash_sha256 == page_hash
        and previous.canonical_url == result.fetched_url
    )


def _indexable_text(extracted: ExtractedPublicContent | None) -> str:
    if extracted is None or extracted.noindex:
        return ""
    return " ".join(
        part
        for part in (
            extracted.text,
            extracted.semantic_text,
            extracted.structured_text,
        )
        if part
    )


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
    extracted: ExtractedPublicContent | None,
) -> tuple[PublicClaim, ...]:
    if extracted is None or extracted.noindex:
        return ()
    claims = list(
        _claims_for_text(
            target,
            resource,
            version,
            " ".join(part for part in (extracted.text, extracted.semantic_text) if part),
            evidence_basis=ClaimEvidenceBasis.TARGET_CONTENT,
        )
    )
    claims.extend(
        _claims_for_text(
            target,
            resource,
            version,
            extracted.structured_text,
            evidence_basis=ClaimEvidenceBasis.STRUCTURED_DATA,
        )
    )
    return tuple(claims)


def _claims_for_text(
    target: PublicWebTarget,
    resource: PublicResource,
    version: PublicResourceVersion,
    text: str,
    *,
    evidence_basis: ClaimEvidenceBasis,
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
                    evidence_basis=evidence_basis,
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
                    evidence_basis=evidence_basis,
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
    *,
    evidence_basis: ClaimEvidenceBasis,
) -> PublicClaim:
    return PublicClaim(
        organization_id=target.organization_id,
        resource_version_id=version.id,
        claim_type=claim_type,
        statement=statement,
        evidence_basis=evidence_basis,
        resolution_status=ClaimResolutionStatus.OBSERVED,
        confidence=1.0,
        corroboration_group_key=resource.corroboration_group_key,
        source_locator=resource.canonical_url,
        excerpt=matched_term,
    )
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

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

NOW = datetime(2026, 8, 5, 20, 0, tzinfo=UTC)
HASH_A = "a" * 64
HASH_B = "b" * 64


def test_resource_identity_is_deterministic_and_corroboration_is_target_based() -> None:
    organization_id = uuid4()
    search_result = _resource(
        organization_id=organization_id,
        kind=PublicResourceKind.SEARCH_RESULT,
        discovery_method=DiscoveryMethod.SEARCH_API,
        source_record_key="search-1",
    )
    target_page = _resource(
        organization_id=organization_id,
        kind=PublicResourceKind.WEB_PAGE,
        discovery_method=DiscoveryMethod.DIRECT,
        source_record_key="page-1",
    )

    assert search_result.identity_key != target_page.identity_key
    assert search_result.corroboration_group_key == target_page.corroboration_group_key
    assert search_result.canonical_url == "https://example.com/security/report?x=1&y=2"


def test_non_public_resource_cannot_be_marked_fetched() -> None:
    with pytest.raises(ValueError, match="non-public"):
        _resource(
            access_state=ResourceAccessState.RESTRICTED,
            retrieval_state=ResourceRetrievalState.FETCHED,
        )


def test_resource_rejects_reverse_timeline() -> None:
    with pytest.raises(ValueError, match="last_seen_at"):
        _resource(last_seen_at=NOW - timedelta(seconds=1))


def test_resource_version_normalizes_metadata_and_has_stable_revision_key() -> None:
    resource = _resource()
    first = PublicResourceVersion(
        resource_key=resource.identity_key,
        source_url="HTTPS://EXAMPLE.COM:443/security/report?y=2&x=1#fragment",
        content_hash_sha256=HASH_A,
        fetched_at=NOW,
        mime_type="Text/HTML; charset=utf-8",
        byte_size=120,
        extracted_text_hash_sha256=HASH_B,
        title="  Security report  ",
        language=" en ",
    )
    second = PublicResourceVersion(
        resource_key=resource.identity_key,
        source_url=resource.canonical_url,
        content_hash_sha256=HASH_A,
        fetched_at=NOW + timedelta(hours=1),
        mime_type="text/html",
        byte_size=120,
    )

    assert first.source_url == resource.canonical_url
    assert first.mime_type == "text/html"
    assert first.title == "Security report"
    assert first.language == "en"
    assert first.version_key == second.version_key


def test_resource_version_rejects_bad_hash_mime_and_size() -> None:
    resource = _resource()
    with pytest.raises(ValueError, match="SHA-256"):
        PublicResourceVersion(
            resource_key=resource.identity_key,
            source_url=resource.canonical_url,
            content_hash_sha256="invalid",
            fetched_at=NOW,
            mime_type="text/html",
            byte_size=1,
        )
    with pytest.raises(ValueError, match="mime_type"):
        PublicResourceVersion(
            resource_key=resource.identity_key,
            source_url=resource.canonical_url,
            content_hash_sha256=HASH_A,
            fetched_at=NOW,
            mime_type="html",
            byte_size=1,
        )
    with pytest.raises(ValueError, match="byte_size"):
        PublicResourceVersion(
            resource_key=resource.identity_key,
            source_url=resource.canonical_url,
            content_hash_sha256=HASH_A,
            fetched_at=NOW,
            mime_type="text/html",
            byte_size=-1,
        )


def test_search_result_metadata_cannot_confirm_a_claim() -> None:
    resource = _resource(
        kind=PublicResourceKind.SEARCH_RESULT,
        discovery_method=DiscoveryMethod.SEARCH_API,
    )
    version = _version(resource)

    with pytest.raises(ValueError, match="cannot confirm"):
        _claim(
            resource,
            version,
            evidence_basis=ClaimEvidenceBasis.SEARCH_RESULT_METADATA,
            resolution_status=ClaimResolutionStatus.CONFIRMED,
        )


def test_projection_deduplicates_equivalent_claims() -> None:
    resource = _resource()
    version = _version(resource)
    first = _claim(resource, version)
    duplicate = _claim(resource, version, statement="  Uses a managed SOC provider. ")

    projection = PublicFootprintProjection(
        resource=resource,
        version=version,
        claims=(first, duplicate),
    )

    assert len(projection.claims) == 1


def test_projection_rejects_mismatched_resource_version_or_claim() -> None:
    resource = _resource()
    other_resource = _resource(organization_id=uuid4())
    wrong_version = _version(other_resource)

    with pytest.raises(ValueError, match="resource version"):
        PublicFootprintProjection(resource=resource, version=wrong_version)

    version = _version(resource)
    wrong_claim = _claim(other_resource, version)
    with pytest.raises(ValueError, match="claim organization"):
        PublicFootprintProjection(
            resource=resource,
            version=version,
            claims=(wrong_claim,),
        )


def _resource(
    *,
    organization_id=None,
    kind: PublicResourceKind = PublicResourceKind.WEB_PAGE,
    discovery_method: DiscoveryMethod = DiscoveryMethod.DIRECT,
    source_record_key: str = "resource-1",
    access_state: ResourceAccessState = ResourceAccessState.PUBLIC,
    retrieval_state: ResourceRetrievalState = ResourceRetrievalState.DISCOVERED,
    last_seen_at: datetime = NOW,
) -> PublicResource:
    return PublicResource(
        organization_id=organization_id or uuid4(),
        source_id="corporate-site",
        source_record_key=source_record_key,
        canonical_url="https://Example.com:443/security/report?y=2&x=1#section",
        source_url="https://example.com/sitemap.xml",
        kind=kind,
        discovery_method=discovery_method,
        first_discovered_at=NOW,
        last_seen_at=last_seen_at,
        access_state=access_state,
        retrieval_state=retrieval_state,
    )


def _version(resource: PublicResource) -> PublicResourceVersion:
    return PublicResourceVersion(
        resource_key=resource.identity_key,
        source_url=resource.canonical_url,
        content_hash_sha256=HASH_A,
        fetched_at=NOW,
        mime_type="text/html",
        byte_size=100,
    )


def _claim(
    resource: PublicResource,
    version: PublicResourceVersion,
    *,
    statement: str = "Uses a managed SOC provider.",
    evidence_basis: ClaimEvidenceBasis = ClaimEvidenceBasis.TARGET_CONTENT,
    resolution_status: ClaimResolutionStatus = ClaimResolutionStatus.CANDIDATE,
) -> PublicClaim:
    return PublicClaim(
        organization_id=resource.organization_id,
        resource_version_id=version.id,
        claim_type=PublicClaimType.PROVIDER_PARTNER_CUSTOMER,
        statement=statement,
        evidence_basis=evidence_basis,
        resolution_status=resolution_status,
        confidence=0.8,
        corroboration_group_key=resource.corroboration_group_key,
        source_locator="main article",
        excerpt="Managed SOC provider",
    )

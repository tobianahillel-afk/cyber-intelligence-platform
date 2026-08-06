from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from cip.modules.public_footprint.domain import (
    ClaimEvidenceBasis,
    ClaimResolutionStatus,
    DiscoveryMethod,
    PublicClaimType,
    PublicResource,
    PublicResourceKind,
    ResourceAccessState,
    ResourceRetrievalState,
    SearchLeadClaim,
    SearchQueryTemplate,
    SearchResultLead,
    map_search_result_lead,
)

NOW = datetime(2026, 8, 6, 9, 0, tzinfo=UTC)
ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000001220")
TARGET_URL = "https://example.com/security-program"


def test_search_result_is_quarantined_candidate_with_shared_target_group() -> None:
    lead = SearchResultLead(
        organization_id=ORGANIZATION_ID,
        source_id="approved-search-api",
        source_record_key="result-42",
        target_url=TARGET_URL,
        title="Example security program",
        snippet="Example describes a zero trust migration on Azure.",
        rank=3,
        observed_at=NOW,
        query_template_id="organization-security-footprint",
        query_template_version=1,
        candidate_claim=SearchLeadClaim(
            claim_type=PublicClaimType.SECURITY_OR_COMPLIANCE_OBJECTIVE,
            statement="Example may be planning a zero trust migration.",
            confidence=0.4,
        ),
    )

    projection = map_search_result_lead(lead)
    claim = projection.claims[0]
    target = _target_resource()

    assert projection.resource.kind is PublicResourceKind.SEARCH_RESULT
    assert projection.resource.access_state is ResourceAccessState.UNKNOWN
    assert projection.resource.retrieval_state is ResourceRetrievalState.QUARANTINED
    assert projection.version.mime_type == "application/x-search-result-metadata"
    assert claim.evidence_basis is ClaimEvidenceBasis.SEARCH_RESULT_METADATA
    assert claim.resolution_status is ClaimResolutionStatus.CANDIDATE
    assert claim.confidence == 0.4
    assert projection.resource.identity_key != target.identity_key
    assert projection.resource.corroboration_group_key == target.corroboration_group_key


def test_search_templates_and_candidate_confidence_are_bounded() -> None:
    template = SearchQueryTemplate(
        id="organization-security-footprint",
        version=2,
        query_pattern='"{organization}" security architecture',
        purpose="corporate-public-footprint",
    )

    assert template.render("Example Corp") == '"Example Corp" security architecture'
    assert not template.enabled
    with pytest.raises(ValueError, match="placeholder"):
        SearchQueryTemplate(
            id="invalid",
            version=1,
            query_pattern="security architecture",
            purpose="corporate-public-footprint",
        )
    with pytest.raises(ValueError, match="confidence"):
        SearchLeadClaim(
            claim_type=PublicClaimType.TECHNOLOGY_OR_ARCHITECTURE,
            statement="Unverified technology claim.",
            confidence=0.8,
        )


def _target_resource() -> PublicResource:
    return PublicResource(
        organization_id=ORGANIZATION_ID,
        source_id="public-web-example",
        source_record_key=TARGET_URL,
        canonical_url=TARGET_URL,
        source_url=TARGET_URL,
        kind=PublicResourceKind.WEB_PAGE,
        discovery_method=DiscoveryMethod.SITEMAP,
        first_discovered_at=NOW,
        last_seen_at=NOW,
        access_state=ResourceAccessState.PUBLIC,
        retrieval_state=ResourceRetrievalState.FETCHED,
        title="Example security program",
    )

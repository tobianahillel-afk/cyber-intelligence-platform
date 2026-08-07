from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cip.adapters.sources.relationship_catalogs.mappers import (
    map_public_relationship_record,
)
from cip.adapters.sources.relationship_catalogs.schemas import (
    OrganizationReference,
    ProviderClaimKind,
    ProviderEvidenceClass,
    ProviderRelationshipRole,
    ProviderSourceKind,
    PublicRelationshipRecord,
)
from cip.modules.relationship_intelligence.domain.models import (
    RelationshipClaimType,
    RelationshipEvidenceClass,
    RelationshipOrganizationLinkStatus,
)

NOW = datetime(2026, 8, 7, 20, 0, tzinfo=UTC)


def test_case_study_maps_to_claimed_not_contracted_evidence() -> None:
    bundle = map_public_relationship_record(
        "case-study-provider",
        _record(
            source_kind=ProviderSourceKind.CASE_STUDY,
            evidence_class=ProviderEvidenceClass.CLAIMED,
        ),
    )

    evidence = bundle.evidence[0]
    assert evidence.evidence_class is RelationshipEvidenceClass.CLAIMED
    assert evidence.contract_reference is None
    assert evidence.source_link_status is RelationshipOrganizationLinkStatus.CANDIDATE
    assert evidence.target_link_status is RelationshipOrganizationLinkStatus.CANDIDATE


def test_partner_directory_exact_ids_map_to_exact_directed_links() -> None:
    source_id = uuid4()
    target_id = uuid4()
    record = _record(
        source_kind=ProviderSourceKind.PARTNER_DIRECTORY,
        evidence_class=ProviderEvidenceClass.OBSERVED,
        source_organization=OrganizationReference(
            claimed_name="Integrator A",
            exact_organization_id=str(source_id),
        ),
        target_organization=OrganizationReference(
            claimed_name="Vendor B",
            exact_organization_id=str(target_id),
        ),
    )

    evidence = map_public_relationship_record("partner-directory", record).evidence[0]

    assert evidence.source_organization_id == source_id
    assert evidence.target_organization_id == target_id
    assert evidence.source_link_status is RelationshipOrganizationLinkStatus.EXACT
    assert evidence.target_link_status is RelationshipOrganizationLinkStatus.EXACT


def test_product_and_service_context_stay_separate_from_evidence() -> None:
    record = _record(
        product_context="Vendor Secure Gateway",
        service_context="network_sase_security",
    )

    bundle = map_public_relationship_record("directory", record)

    assert bundle.evidence[0].product_context == "Vendor Secure Gateway"
    assert {context.context_type for context in bundle.contexts} == {"product", "service"}
    assert {context.value for context in bundle.contexts} == {
        "Vendor Secure Gateway",
        "network_sase_security",
    }


def test_retraction_maps_as_current_retraction_revision() -> None:
    record = _record(
        claim_kind=ProviderClaimKind.RETRACTION,
        supersedes_record_id="previous-record",
    )

    evidence = map_public_relationship_record("disclosure", record).evidence[0]

    assert evidence.claim_type is RelationshipClaimType.RETRACTION
    assert evidence.active is True
    assert evidence.supersedes_record_key == "previous-record"


def test_invalid_exact_organization_identifier_is_rejected() -> None:
    record = _record(
        source_organization=OrganizationReference(
            claimed_name="Provider A",
            exact_organization_id="not-a-uuid",
        )
    )

    with pytest.raises(ValueError, match="must be a UUID"):
        map_public_relationship_record("disclosure", record)


def test_schema_rejects_same_exact_relationship_endpoints() -> None:
    organization_id = str(uuid4())

    with pytest.raises(ValueError, match="different organizations"):
        _record(
            source_organization=OrganizationReference(
                claimed_name="Same A",
                exact_organization_id=organization_id,
            ),
            target_organization=OrganizationReference(
                claimed_name="Same A",
                exact_organization_id=organization_id,
            ),
        )


def _record(
    *,
    source_kind: ProviderSourceKind = ProviderSourceKind.OFFICIAL_DISCLOSURE,
    evidence_class: ProviderEvidenceClass = ProviderEvidenceClass.CLAIMED,
    claim_kind: ProviderClaimKind = ProviderClaimKind.ASSERTION,
    source_organization: OrganizationReference | None = None,
    target_organization: OrganizationReference | None = None,
    product_context: str | None = None,
    service_context: str | None = None,
    supersedes_record_id: str | None = None,
) -> PublicRelationshipRecord:
    return PublicRelationshipRecord(
        record_id="record-1",
        relationship_key="provider-a:customer-b:provider",
        source_url="https://example.org/relationships/1",
        source_kind=source_kind,
        role=ProviderRelationshipRole.PROVIDER,
        evidence_class=evidence_class,
        claim_kind=claim_kind,
        title="Provider A relationship with Customer B",
        excerpt="Bounded public metadata describing a professional relationship.",
        source_organization=source_organization
        or OrganizationReference(claimed_name="Provider A"),
        target_organization=target_organization
        or OrganizationReference(claimed_name="Customer B"),
        published_at=NOW - timedelta(days=2),
        modified_at=NOW - timedelta(days=1),
        observed_at=NOW,
        product_context=product_context,
        service_context=service_context,
        independence_key="original-source",
        confidence=0.8,
        supersedes_record_id=supersedes_record_id,
    )

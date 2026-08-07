from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from cip.modules.relationship_intelligence.domain.models import (
    MAX_RELATIONSHIP_EXCERPT_LENGTH,
    RelationshipClaimType,
    RelationshipEvidenceClass,
    RelationshipEvidenceSnapshot,
    RelationshipOrganizationLinkStatus,
    RelationshipRole,
    RelationshipSourceKind,
    RelationshipStatus,
)
from cip.modules.relationship_intelligence.domain.reconciliation import (
    reconcile_relationship_evidence,
)

NOW = datetime(2026, 8, 7, 18, 30, tzinfo=UTC)


def test_marketing_claim_stays_claimed_not_active() -> None:
    snapshot = _evidence(
        source_kind=RelationshipSourceKind.CASE_STUDY,
        evidence_class=RelationshipEvidenceClass.CLAIMED,
    )

    relationship = reconcile_relationship_evidence((snapshot,), now=NOW)[0]

    assert relationship.status is RelationshipStatus.CLAIMED
    assert relationship.has_contract_evidence is False
    assert relationship.contract_backed_current is False


def test_current_contract_can_support_active_incumbent_context() -> None:
    snapshot = _evidence(
        source_kind=RelationshipSourceKind.PROCUREMENT,
        evidence_class=RelationshipEvidenceClass.CONTRACTED,
        contract_reference="contract-2026-42",
        renewal_at=NOW + timedelta(days=90),
    )

    relationship = reconcile_relationship_evidence((snapshot,), now=NOW)[0]

    assert relationship.status is RelationshipStatus.ACTIVE
    assert relationship.has_contract_evidence is True
    assert relationship.contract_backed_current is True
    assert relationship.next_renewal_at == NOW + timedelta(days=90)


def test_historical_contract_is_not_current_incumbent() -> None:
    snapshot = _evidence(
        source_kind=RelationshipSourceKind.PROCUREMENT,
        evidence_class=RelationshipEvidenceClass.CONTRACTED,
        contract_reference="old-contract",
        valid_from=NOW - timedelta(days=700),
        valid_until=NOW - timedelta(days=365),
    )

    relationship = reconcile_relationship_evidence((snapshot,), now=NOW)[0]

    assert relationship.status is RelationshipStatus.HISTORICAL
    assert relationship.has_contract_evidence is False
    assert relationship.contract_backed_current is False


def test_inferred_relationship_stays_inferred() -> None:
    snapshot = _evidence(
        source_kind=RelationshipSourceKind.PASSIVE_OBSERVATION,
        evidence_class=RelationshipEvidenceClass.INFERRED,
    )

    relationship = reconcile_relationship_evidence((snapshot,), now=NOW)[0]

    assert relationship.status is RelationshipStatus.INFERRED
    assert relationship.contract_backed_current is False


def test_observed_current_relationship_can_be_active_without_contract() -> None:
    snapshot = _evidence(
        source_kind=RelationshipSourceKind.CERTIFICATE,
        evidence_class=RelationshipEvidenceClass.OBSERVED,
    )

    relationship = reconcile_relationship_evidence((snapshot,), now=NOW)[0]

    assert relationship.status is RelationshipStatus.ACTIVE
    assert relationship.has_contract_evidence is False
    assert relationship.contract_backed_current is False


def test_role_conflict_requires_review() -> None:
    provider = _evidence(
        source_kind=RelationshipSourceKind.PROCUREMENT,
        evidence_class=RelationshipEvidenceClass.CONTRACTED,
        contract_reference="contract-a",
    )
    reseller = replace(
        provider,
        source_id="directory-b",
        source_record_key="record-b",
        source_url="https://partners.example.com/b",
        source_kind=RelationshipSourceKind.PARTNER_DIRECTORY,
        role=RelationshipRole.RESELLER,
        evidence_class=RelationshipEvidenceClass.OBSERVED,
        contract_reference=None,
        independence_key="directory-b",
    )

    relationship = reconcile_relationship_evidence((provider, reseller), now=NOW)[0]

    assert relationship.status is RelationshipStatus.UNDER_REVIEW
    assert relationship.has_role_conflict is True


def test_conflicting_exact_source_links_require_review() -> None:
    first = _evidence(
        source_organization_id=uuid4(),
        source_link_status=RelationshipOrganizationLinkStatus.EXACT,
    )
    second = replace(
        first,
        source_id="source-b",
        source_record_key="record-b",
        source_url="https://example.org/b",
        source_organization_id=uuid4(),
        independence_key="source-b",
    )

    relationship = reconcile_relationship_evidence((first, second), now=NOW)[0]

    assert relationship.source_organization_id is None
    assert relationship.source_link_status is RelationshipOrganizationLinkStatus.REVIEW_REQUIRED


def test_superseding_retraction_removes_old_assertion() -> None:
    assertion = _evidence()
    retraction = replace(
        assertion,
        source_record_key="record-r2",
        claim_type=RelationshipClaimType.RETRACTION,
        modified_at=NOW + timedelta(minutes=1),
        supersedes_record_key=assertion.source_record_key,
    )

    relationship = reconcile_relationship_evidence((assertion, retraction), now=NOW)[0]

    assert relationship.status is RelationshipStatus.RETRACTED
    assert relationship.evidence_count == 1
    assert relationship.has_retraction is True


def test_expired_claim_becomes_stale() -> None:
    snapshot = _evidence(
        evidence_class=RelationshipEvidenceClass.CLAIMED,
        expires_at=NOW - timedelta(minutes=1),
    )

    relationship = reconcile_relationship_evidence((snapshot,), now=NOW)[0]

    assert relationship.status is RelationshipStatus.STALE


def test_contract_context_rejected_on_marketing_claim() -> None:
    with pytest.raises(ValueError, match="contract reference"):
        _evidence(
            source_kind=RelationshipSourceKind.CASE_STUDY,
            evidence_class=RelationshipEvidenceClass.CLAIMED,
            contract_reference="not-a-contract-proof",
        )


def test_source_and_target_must_not_resolve_to_same_organization() -> None:
    organization_id = uuid4()

    with pytest.raises(ValueError, match="must differ"):
        _evidence(
            source_organization_id=organization_id,
            target_organization_id=organization_id,
            source_link_status=RelationshipOrganizationLinkStatus.EXACT,
            target_link_status=RelationshipOrganizationLinkStatus.EXACT,
        )


def test_excerpt_is_bounded() -> None:
    with pytest.raises(ValueError, match="excerpt"):
        _evidence(excerpt="x" * (MAX_RELATIONSHIP_EXCERPT_LENGTH + 1))


def _evidence(
    *,
    source_id: str = "source-a",
    source_kind: RelationshipSourceKind = RelationshipSourceKind.OFFICIAL_DISCLOSURE,
    source_record_key: str = "record-a",
    role: RelationshipRole = RelationshipRole.PROVIDER,
    evidence_class: RelationshipEvidenceClass = RelationshipEvidenceClass.OBSERVED,
    claim_type: RelationshipClaimType = RelationshipClaimType.ASSERTION,
    source_organization_id: UUID | None = None,
    target_organization_id: UUID | None = None,
    source_link_status: RelationshipOrganizationLinkStatus = (
        RelationshipOrganizationLinkStatus.CANDIDATE
    ),
    target_link_status: RelationshipOrganizationLinkStatus = (
        RelationshipOrganizationLinkStatus.CANDIDATE
    ),
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    expires_at: datetime | None = None,
    renewal_at: datetime | None = None,
    contract_reference: str | None = None,
    excerpt: str = "Public relationship metadata.",
) -> RelationshipEvidenceSnapshot:
    return RelationshipEvidenceSnapshot(
        source_id=source_id,
        source_kind=source_kind,
        source_record_key=source_record_key,
        source_url="https://example.org/relationship",
        relationship_key="provider-a:customer-b:provider",
        claim_type=claim_type,
        role=role,
        evidence_class=evidence_class,
        title="Provider A supplies services to Customer B",
        excerpt=excerpt,
        claimed_source_organization_name="Provider A",
        claimed_target_organization_name="Customer B",
        source_organization_id=source_organization_id,
        target_organization_id=target_organization_id,
        source_link_status=source_link_status,
        target_link_status=target_link_status,
        published_at=NOW - timedelta(days=2),
        modified_at=NOW - timedelta(days=1),
        observed_at=NOW - timedelta(hours=3),
        valid_from=valid_from,
        valid_until=valid_until,
        expires_at=expires_at,
        contract_reference=contract_reference,
        renewal_at=renewal_at,
        independence_key=source_id,
        confidence=0.85,
    )

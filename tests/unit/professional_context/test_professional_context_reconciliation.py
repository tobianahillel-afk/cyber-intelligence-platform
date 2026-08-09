from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from cip.modules.professional_context.domain import (
    CommunityAcquisitionMode,
    ContactChannelType,
    ContactEvidenceScope,
    EmploymentState,
    LawfulBasis,
    OrganizationLinkStatus,
    ProfessionalClaimType,
    ProfessionalContactEvidence,
    ProfessionalProcessingContext,
    ProfessionalReviewState,
    ProfessionalRoleClaim,
    PublicCommunityContext,
    ReportingLineClaim,
    reconcile_community_context,
    reconcile_contact_evidence,
    reconcile_reporting_claims,
    reconcile_role_claims,
)

NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
ORG_ID = uuid4()


def _processing() -> ProfessionalProcessingContext:
    return ProfessionalProcessingContext(
        lawful_basis=LawfulBasis.LEGITIMATE_INTERESTS,
        lawful_basis_reference="privacy-review:lot21",
        purpose="professional research",
        reviewed_at=NOW - timedelta(days=30),
        retention_until=NOW + timedelta(days=1000),
    )


def test_role_correction_supersedes_old_revision_without_erasing_history() -> None:
    original = _role(
        source_record_key="role-v1",
        title="Security Manager",
        observed_at=NOW - timedelta(days=10),
    )
    corrected = _role(
        source_record_key="role-v2",
        title="Chief Information Security Officer",
        observed_at=NOW - timedelta(days=1),
        claim_type=ProfessionalClaimType.CORRECTION,
        supersedes_record_key="role-v1",
    )

    projection = reconcile_role_claims((original, corrected), now=NOW)

    assert projection.role_title == "Chief Information Security Officer"
    assert projection.employment_state is EmploymentState.CURRENT
    assert projection.evidence_count == 1
    assert projection.first_observed_at == original.observed_at
    assert projection.last_observed_at == corrected.observed_at


def test_role_retraction_removes_current_employment_but_preserves_timeline() -> None:
    original = _role(
        source_record_key="role-v1",
        title="Security Manager",
        observed_at=NOW - timedelta(days=10),
    )
    retraction = _role(
        source_record_key="role-v2",
        title="Security Manager",
        observed_at=NOW - timedelta(days=1),
        claim_type=ProfessionalClaimType.RETRACTION,
        supersedes_record_key="role-v1",
    )

    projection = reconcile_role_claims((original, retraction), now=NOW)

    assert projection.employment_state is EmploymentState.RETRACTED
    assert projection.first_observed_at == original.observed_at
    assert projection.last_observed_at == retraction.observed_at


def test_conflicting_live_role_claims_require_review_and_drop_resolved_org() -> None:
    first = _role(
        source_record_key="source-a-role",
        title="CISO",
        observed_at=NOW - timedelta(days=2),
        source_id="source-a",
    )
    second = ProfessionalRoleClaim(
        claim_key="role:alice:security-lead",
        person_key="professional-person:alice",
        source_id="source-b",
        source_record_key="source-b-role",
        role_title="CTO",
        observed_at=NOW - timedelta(days=1),
        confidence=0.8,
        processing=_processing(),
        organization_id=uuid4(),
        claimed_organization_name="Other Corp",
        organization_link_status=OrganizationLinkStatus.EXACT,
        review_state=ProfessionalReviewState.CONFIRMED,
    )

    projection = reconcile_role_claims((first, second), now=NOW)

    assert projection.review_state is ProfessionalReviewState.REVIEW_REQUIRED
    assert projection.organization_id is None


def test_contact_retraction_supersedes_business_email() -> None:
    original = _contact(
        source_record_key="contact-v1",
        value="alice@example.org",
        observed_at=NOW - timedelta(days=5),
    )
    retraction = _contact(
        source_record_key="contact-v2",
        value="alice@example.org",
        observed_at=NOW - timedelta(days=1),
        claim_type=ProfessionalClaimType.RETRACTION,
        supersedes_record_key="contact-v1",
    )

    projection = reconcile_contact_evidence((original, retraction), now=NOW)

    assert projection.current is False


def test_conflicting_contact_values_require_review_instead_of_selection() -> None:
    first = _contact(
        source_record_key="contact-a",
        value="alice@example.org",
        observed_at=NOW - timedelta(days=2),
        source_id="source-a",
    )
    second = _contact(
        source_record_key="contact-b",
        value="alice@other.example",
        observed_at=NOW - timedelta(days=1),
        source_id="source-b",
    )

    projection = reconcile_contact_evidence((first, second), now=NOW)

    assert projection.current is False
    assert projection.review_state is ProfessionalReviewState.REVIEW_REQUIRED


def test_reporting_correction_replaces_only_superseded_source_revision() -> None:
    original = _reporting(
        source_record_key="reporting-v1",
        manager="professional-person:bob",
        observed_at=NOW - timedelta(days=5),
    )
    corrected = _reporting(
        source_record_key="reporting-v2",
        manager="professional-person:bob",
        observed_at=NOW - timedelta(days=1),
        claim_type=ProfessionalClaimType.CORRECTION,
        supersedes_record_key="reporting-v1",
    )

    projection = reconcile_reporting_claims((original, corrected), now=NOW)

    assert projection.current is True
    assert projection.last_observed_at == corrected.observed_at


def test_community_retraction_removes_current_context() -> None:
    original = _community(
        source_record_key="community-v1",
        observed_at=NOW - timedelta(days=5),
    )
    retraction = _community(
        source_record_key="community-v2",
        observed_at=NOW - timedelta(days=1),
        claim_type=ProfessionalClaimType.RETRACTION,
        supersedes_record_key="community-v1",
    )

    projection = reconcile_community_context((original, retraction), now=NOW)

    assert projection.current is False


def _role(
    *,
    source_record_key: str,
    title: str,
    observed_at: datetime,
    source_id: str = "organization-site",
    claim_type: ProfessionalClaimType = ProfessionalClaimType.ASSERTION,
    supersedes_record_key: str | None = None,
) -> ProfessionalRoleClaim:
    return ProfessionalRoleClaim(
        claim_key="role:alice:security-lead",
        person_key="professional-person:alice",
        source_id=source_id,
        source_record_key=source_record_key,
        role_title=title,
        observed_at=observed_at,
        confidence=0.9,
        processing=_processing(),
        organization_id=ORG_ID,
        claimed_organization_name="Example Corp",
        organization_link_status=OrganizationLinkStatus.EXACT,
        review_state=ProfessionalReviewState.CONFIRMED,
        claim_type=claim_type,
        supersedes_record_key=supersedes_record_key,
    )


def _contact(
    *,
    source_record_key: str,
    value: str,
    observed_at: datetime,
    source_id: str = "organization-site",
    claim_type: ProfessionalClaimType = ProfessionalClaimType.ASSERTION,
    supersedes_record_key: str | None = None,
) -> ProfessionalContactEvidence:
    return ProfessionalContactEvidence(
        contact_key="contact:alice:business-email",
        channel_type=ContactChannelType.BUSINESS_EMAIL,
        evidence_scope=ContactEvidenceScope.ORGANIZATION_PUBLISHED,
        value=value,
        source_id=source_id,
        source_record_key=source_record_key,
        observed_at=observed_at,
        confidence=0.9,
        processing=_processing(),
        person_key="professional-person:alice",
        organization_id=ORG_ID,
        claim_type=claim_type,
        review_state=ProfessionalReviewState.CONFIRMED,
        supersedes_record_key=supersedes_record_key,
    )


def _reporting(
    *,
    source_record_key: str,
    manager: str,
    observed_at: datetime,
    claim_type: ProfessionalClaimType = ProfessionalClaimType.ASSERTION,
    supersedes_record_key: str | None = None,
) -> ReportingLineClaim:
    return ReportingLineClaim(
        claim_key="reporting:alice:bob",
        subject_person_key="professional-person:alice",
        manager_person_key=manager,
        source_id="organization-site",
        source_record_key=source_record_key,
        observed_at=observed_at,
        confidence=0.8,
        processing=_processing(),
        organization_id=ORG_ID,
        claim_type=claim_type,
        review_state=ProfessionalReviewState.CONFIRMED,
        supersedes_record_key=supersedes_record_key,
    )


def _community(
    *,
    source_record_key: str,
    observed_at: datetime,
    claim_type: ProfessionalClaimType = ProfessionalClaimType.ASSERTION,
    supersedes_record_key: str | None = None,
) -> PublicCommunityContext:
    return PublicCommunityContext(
        context_key="community:alice:event",
        community_name="Security Association",
        context_type="public_event_speaker",
        context_value="Annual security conference",
        acquisition_mode=CommunityAcquisitionMode.AUTHORIZED_EXPORT,
        authorization_reference="approval:community-export",
        source_id="authorized-community-export",
        source_record_key=source_record_key,
        observed_at=observed_at,
        confidence=0.8,
        processing=_processing(),
        person_key="professional-person:alice",
        claim_type=claim_type,
        review_state=ProfessionalReviewState.CONFIRMED,
        supersedes_record_key=supersedes_record_key,
    )

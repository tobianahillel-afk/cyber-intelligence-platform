from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cip.modules.data_governance.domain.suppression import SuppressionChannel
from cip.modules.professional_context.domain import (
    CommunityAcquisitionMode,
    ContactChannelType,
    ContactEvidenceScope,
    EmploymentState,
    LawfulBasis,
    OrganizationLinkStatus,
    ProfessionalClaimType,
    ProfessionalContactEvidence,
    ProfessionalPersonReference,
    ProfessionalProcessingContext,
    ProfessionalRoleClaim,
    ProfessionalServiceRelevance,
    PublicCommunityContext,
    ReportingLineClaim,
    source_person_key,
)
from cip.modules.service_taxonomy.domain.models import CyberServiceFamily

NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)


def _processing() -> ProfessionalProcessingContext:
    return ProfessionalProcessingContext(
        lawful_basis=LawfulBasis.LEGITIMATE_INTERESTS,
        lawful_basis_reference="privacy-review:professional-context-v1",
        purpose="professional organization research",
        reviewed_at=NOW,
        retention_until=NOW + timedelta(days=1095),
    )


def test_same_name_from_different_sources_never_shares_person_key() -> None:
    first_key = source_person_key("directory-a", "alice-1")
    second_key = source_person_key("directory-b", "alice-1")

    first = ProfessionalPersonReference(
        person_key=first_key,
        display_name="Alice Martin",
        source_id="directory-a",
        source_kind="public_professional_directory",
        source_record_key="alice-1",
        source_url="https://directory-a.example/alice-1",
        observed_at=NOW,
        confidence=0.8,
        processing=_processing(),
    )
    second = ProfessionalPersonReference(
        person_key=second_key,
        display_name="Alice Martin",
        source_id="directory-b",
        source_kind="public_professional_directory",
        source_record_key="alice-1",
        source_url="https://directory-b.example/alice-1",
        observed_at=NOW,
        confidence=0.8,
        processing=_processing(),
    )

    assert first.display_name == second.display_name
    assert first.person_key != second.person_key
    assert first.authorizes_outreach is False
    assert first.authorizes_source_automation is False


def test_person_key_cannot_be_replaced_by_name_derived_identifier() -> None:
    with pytest.raises(ValueError, match="source person_key"):
        ProfessionalPersonReference(
            person_key="professional-person:alice-martin",
            display_name="Alice Martin",
            source_id="directory-a",
            source_kind="public_professional_directory",
            source_record_key="alice-1",
            observed_at=NOW,
            confidence=0.8,
            processing=_processing(),
        )


def test_role_state_distinguishes_current_stale_and_historical() -> None:
    organization_id = uuid4()
    current = _role_claim(
        organization_id=organization_id,
        observed_at=NOW - timedelta(days=30),
    )
    stale = _role_claim(
        organization_id=organization_id,
        observed_at=NOW - timedelta(days=500),
    )
    historical = _role_claim(
        organization_id=organization_id,
        observed_at=NOW - timedelta(days=500),
        valid_until=NOW - timedelta(days=20),
    )

    assert current.employment_state_at(NOW) is EmploymentState.CURRENT
    assert stale.employment_state_at(NOW) is EmploymentState.STALE
    assert historical.employment_state_at(NOW) is EmploymentState.HISTORICAL


def test_retracted_and_disputed_roles_never_look_current() -> None:
    retracted = _role_claim(
        organization_id=uuid4(),
        claim_type=ProfessionalClaimType.RETRACTION,
    )
    disputed = _role_claim(
        organization_id=uuid4(),
        claim_type=ProfessionalClaimType.DISPUTE,
    )

    assert retracted.employment_state_at(NOW) is EmploymentState.RETRACTED
    assert disputed.employment_state_at(NOW) is EmploymentState.DISPUTED


def test_non_exact_organization_link_cannot_carry_resolved_id() -> None:
    with pytest.raises(ValueError, match="non-exact"):
        _role_claim(
            organization_id=uuid4(),
            organization_link_status=OrganizationLinkStatus.REVIEW_REQUIRED,
        )


def test_reporting_line_is_directed_non_transitive_and_not_self_referential() -> None:
    claim = ReportingLineClaim(
        claim_key="reporting:alice:bob",
        subject_person_key="professional-person:alice",
        manager_person_key="professional-person:bob",
        source_id="org-page",
        source_record_key="team-page-1",
        source_url="https://example.org/team",
        observed_at=NOW,
        confidence=0.7,
        processing=_processing(),
    )

    assert claim.permits_transitive_inference is False

    with pytest.raises(ValueError, match="self-referential"):
        ReportingLineClaim(
            claim_key="reporting:alice:alice",
            subject_person_key="professional-person:alice",
            manager_person_key="professional-person:alice",
            source_id="org-page",
            source_record_key="team-page-2",
            observed_at=NOW,
            confidence=0.7,
            processing=_processing(),
        )


def test_contact_model_has_no_personal_channel_type() -> None:
    with pytest.raises(ValueError):
        ContactChannelType("personal_phone")


def test_switchboard_is_organization_level_and_uses_organization_suppression() -> None:
    contact = ProfessionalContactEvidence(
        contact_key="switchboard:example",
        channel_type=ContactChannelType.SWITCHBOARD,
        evidence_scope=ContactEvidenceScope.ORGANIZATION_PUBLISHED,
        value="+33 1 23 45 67 89",
        source_id="organization-site",
        source_record_key="contact-page",
        source_url="https://example.org/contact",
        observed_at=NOW,
        confidence=1.0,
        processing=_processing(),
        organization_id=uuid4(),
    )

    assert contact.suppression_channel is SuppressionChannel.ORGANIZATION
    assert contact.authorizes_outreach is False


def test_switchboard_cannot_be_attached_as_personal_phone() -> None:
    with pytest.raises(ValueError, match="organization-level"):
        ProfessionalContactEvidence(
            contact_key="switchboard:person",
            channel_type=ContactChannelType.SWITCHBOARD,
            evidence_scope=ContactEvidenceScope.PUBLIC_PROFESSIONAL,
            value="+33 1 23 45 67 89",
            source_id="public-page",
            source_record_key="person-page",
            observed_at=NOW,
            confidence=0.8,
            processing=_processing(),
            organization_id=uuid4(),
            person_key="professional-person:alice",
        )


def test_professional_profile_is_reference_not_automation_authorization() -> None:
    contact = ProfessionalContactEvidence(
        contact_key="profile:alice",
        channel_type=ContactChannelType.PROFESSIONAL_PROFILE,
        evidence_scope=ContactEvidenceScope.PUBLIC_PROFESSIONAL,
        value="https://profiles.example/alice",
        source_id="approved-directory",
        source_record_key="alice-profile",
        observed_at=NOW,
        confidence=0.8,
        processing=_processing(),
        person_key="professional-person:alice",
    )

    assert contact.suppression_channel is SuppressionChannel.PROFESSIONAL_PROFILE
    assert contact.authorizes_source_automation is False
    assert contact.authorizes_outreach is False


def test_community_context_requires_explicit_authorization_reference_and_metadata_only() -> None:
    context = PublicCommunityContext(
        context_key="community:event:alice",
        community_name="Security Association",
        context_type="public_event_speaker",
        context_value="Annual security conference",
        acquisition_mode=CommunityAcquisitionMode.AUTHORIZED_EXPORT,
        authorization_reference="approval:community-export-2026-08",
        source_id="authorized-community-export",
        source_record_key="speaker-42",
        observed_at=NOW,
        confidence=0.9,
        processing=_processing(),
        person_key="professional-person:alice",
    )

    assert context.metadata_only is True
    assert context.authorizes_source_automation is False
    assert context.authorizes_outreach is False

    with pytest.raises(ValueError, match="authorization_reference"):
        PublicCommunityContext(
            context_key="community:event:bob",
            community_name="Security Association",
            context_type="public_event_speaker",
            context_value="Annual security conference",
            acquisition_mode=CommunityAcquisitionMode.AUTHORIZED_EXPORT,
            authorization_reference="",
            source_id="authorized-community-export",
            source_record_key="speaker-43",
            observed_at=NOW,
            confidence=0.9,
            processing=_processing(),
            person_key="professional-person:bob",
        )


def test_service_relevance_never_creates_signal_opportunity_or_outreach() -> None:
    relevance = ProfessionalServiceRelevance(
        mapping_key="relevance:alice:grc",
        service_family=CyberServiceFamily.GRC_COMPLIANCE,
        rationale="Public role title indicates governance responsibility for analyst review.",
        confidence=0.7,
        source_claim_keys=("role:alice:ciso",),
        created_at=NOW,
        person_key="professional-person:alice",
    )

    assert relevance.creates_commercial_signal is False
    assert relevance.creates_opportunity is False
    assert relevance.authorizes_outreach is False


def test_processing_context_expires_at_retention_deadline() -> None:
    processing = _processing()

    assert processing.permits_processing_at(NOW + timedelta(days=1094)) is True
    assert processing.permits_processing_at(NOW + timedelta(days=1095)) is False


def _role_claim(
    *,
    organization_id,
    observed_at: datetime = NOW,
    valid_until: datetime | None = None,
    claim_type: ProfessionalClaimType = ProfessionalClaimType.ASSERTION,
    organization_link_status: OrganizationLinkStatus = OrganizationLinkStatus.EXACT,
) -> ProfessionalRoleClaim:
    return ProfessionalRoleClaim(
        claim_key=f"role:alice:{observed_at.isoformat()}:{claim_type.value}",
        person_key="professional-person:alice",
        source_id="organization-site",
        source_record_key=f"role-{observed_at.timestamp()}-{claim_type.value}",
        role_title="Chief Information Security Officer",
        observed_at=observed_at,
        confidence=0.9,
        processing=_processing(),
        organization_id=organization_id,
        claimed_organization_name="Example Corp",
        organization_link_status=organization_link_status,
        valid_from=observed_at,
        valid_until=valid_until,
        claim_type=claim_type,
    )

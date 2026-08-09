from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select

from cip.modules.data_governance.domain.suppression import (
    SuppressionChannel,
    SuppressionReason,
    hash_identifier,
)
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.professional_context.domain import (
    CommunityAcquisitionMode,
    ContactChannelType,
    ContactEvidenceScope,
    LawfulBasis,
    OrganizationLinkStatus,
    ProfessionalContactEvidence,
    ProfessionalPersonReference,
    ProfessionalProcessingContext,
    ProfessionalReviewState,
    ProfessionalRoleClaim,
    ProfessionalServiceRelevance,
    PublicCommunityContext,
    ReportingLineClaim,
    source_person_key,
)
from cip.modules.professional_context.infrastructure.community_persistence import (
    persist_community_context,
)
from cip.modules.professional_context.infrastructure.contact_models import (
    ProfessionalContactRecord,
    ProfessionalContactSnapshotRecord,
)
from cip.modules.professional_context.infrastructure.contact_persistence import (
    persist_professional_contacts,
)
from cip.modules.professional_context.infrastructure.context_models import (
    ProfessionalCommunityRecord,
    ProfessionalCommunitySnapshotRecord,
    ProfessionalServiceRelevanceRecord,
)
from cip.modules.professional_context.infrastructure.person_models import (
    ProfessionalPersonRecord,
    ProfessionalPersonSnapshotRecord,
)
from cip.modules.professional_context.infrastructure.person_persistence import (
    persist_professional_people,
)
from cip.modules.professional_context.infrastructure.privacy_lifecycle import (
    erase_professional_person,
)
from cip.modules.professional_context.infrastructure.reporting_persistence import (
    persist_reporting_lines,
)
from cip.modules.professional_context.infrastructure.relevance_persistence import (
    persist_service_relevance,
)
from cip.modules.professional_context.infrastructure.role_models import (
    ProfessionalReportingLineRecord,
    ProfessionalReportingSnapshotRecord,
    ProfessionalRoleRecord,
    ProfessionalRoleSnapshotRecord,
)
from cip.modules.professional_context.infrastructure.role_persistence import (
    persist_professional_roles,
)
from cip.modules.service_taxonomy.domain.models import CyberServiceFamily
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
PEPPER = b"lot21-test-pepper"
RAW_EMAIL = "alice@example.org"


def test_erasure_redacts_raw_values_and_replay_cannot_restore_them() -> None:
    session = _session()
    organization = _organization(session)
    person = _person()
    person_key = person.person_key
    persist_professional_people(session, (person,), now=NOW)
    persist_professional_roles(
        session,
        (_role(person_key, organization.id),),
        now=NOW,
    )
    persist_reporting_lines(
        session,
        (_reporting(person_key, organization.id),),
        now=NOW,
    )
    persist_professional_contacts(
        session,
        (_contact(person_key, organization.id),),
        now=NOW,
    )
    persist_community_context(
        session,
        (_community(person_key, organization.id),),
        now=NOW,
    )
    persist_service_relevance(
        session,
        (
            ProfessionalServiceRelevance(
                mapping_key="service-relevance:alice:grc",
                service_family=CyberServiceFamily.GRC_COMPLIANCE,
                rationale="Professional governance role for analyst navigation.",
                confidence=0.7,
                source_claim_keys=("role:alice:example-security",),
                created_at=NOW,
                person_key=person_key,
            ),
        ),
        now=NOW,
    )

    audit = erase_professional_person(
        session,
        person_key=person_key,
        identifier=RAW_EMAIL,
        channel=SuppressionChannel.EMAIL,
        reason=SuppressionReason.DATA_SUBJECT_REQUEST,
        pepper=PEPPER,
        now=NOW + timedelta(minutes=5),
        minimum_retention_days=365,
        source="privacy-request",
        actor="privacy-analyst@example.test",
    )
    session.flush()

    person_record = session.scalar(select(ProfessionalPersonRecord))
    person_snapshot = session.scalar(select(ProfessionalPersonSnapshotRecord))
    role = session.scalar(select(ProfessionalRoleRecord))
    role_snapshot = session.scalar(select(ProfessionalRoleSnapshotRecord))
    reporting = session.scalar(select(ProfessionalReportingLineRecord))
    reporting_snapshot = session.scalar(select(ProfessionalReportingSnapshotRecord))
    contact = session.scalar(select(ProfessionalContactRecord))
    contact_snapshot = session.scalar(select(ProfessionalContactSnapshotRecord))
    community = session.scalar(select(ProfessionalCommunityRecord))
    community_snapshot = session.scalar(select(ProfessionalCommunitySnapshotRecord))

    assert person_record is not None and person_record.display_name is None
    assert person_record.deleted is True and person_record.current is False
    assert person_snapshot is not None and person_snapshot.display_name is None
    assert person_snapshot.source_record_key is None and person_snapshot.source_url is None
    assert role is not None and role.role_title is None and role.deleted is True
    assert role_snapshot is not None and role_snapshot.source_record_key is None
    assert role_snapshot.role_title is None and role_snapshot.source_url is None
    assert reporting is not None and reporting.current is False and reporting.deleted is True
    assert reporting_snapshot is not None and reporting_snapshot.source_record_key is None
    assert contact is not None and contact.value is None and contact.current is False
    assert contact_snapshot is not None and contact_snapshot.value is None
    assert contact_snapshot.source_record_key is None and contact_snapshot.source_url is None
    assert community is not None and community.context_value is None
    assert community_snapshot is not None and community_snapshot.context_value is None
    assert community_snapshot.source_record_key is None
    assert session.scalar(select(func.count()).select_from(ProfessionalServiceRelevanceRecord)) == 0

    expected_hash = hash_identifier(RAW_EMAIL, SuppressionChannel.EMAIL, PEPPER)
    assert audit.subject_hash == expected_hash
    assert audit.subject_hash != RAW_EMAIL
    assert len(audit.subject_hash) == 64
    assert RAW_EMAIL not in str(audit.__dict__)

    snapshot_count = session.scalar(
        select(func.count()).select_from(ProfessionalPersonSnapshotRecord)
    )
    persist_professional_people(session, (person,), now=NOW + timedelta(minutes=10))
    replayed = session.scalar(select(ProfessionalPersonRecord))
    assert replayed is not None and replayed.display_name is None and replayed.deleted is True
    assert session.scalar(select(func.count()).select_from(ProfessionalPersonSnapshotRecord)) == snapshot_count


def _session():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return create_session_factory(engine)()


def _processing() -> ProfessionalProcessingContext:
    return ProfessionalProcessingContext(
        lawful_basis=LawfulBasis.LEGITIMATE_INTERESTS,
        lawful_basis_reference="privacy-review:lot21",
        purpose="professional research",
        reviewed_at=NOW - timedelta(days=1),
        retention_until=NOW + timedelta(days=1095),
    )


def _person() -> ProfessionalPersonReference:
    source_id = "approved-directory"
    source_record_key = "alice-42"
    return ProfessionalPersonReference(
        person_key=source_person_key(source_id, source_record_key),
        display_name="Alice Martin",
        source_id=source_id,
        source_kind="authorized_directory",
        source_record_key=source_record_key,
        source_url="https://directory.example/alice-42",
        observed_at=NOW,
        confidence=0.9,
        processing=_processing(),
        review_state=ProfessionalReviewState.CONFIRMED,
    )


def _organization(session) -> OrganizationRecord:
    record = OrganizationRecord(
        id=uuid4(),
        canonical_name="Example Corp",
        legal_name="Example Corp SAS",
        country_code="FR",
        website_url="https://example.org",
        registration_ids=[],
        created_at=NOW,
        updated_at=NOW,
    )
    session.add(record)
    session.flush()
    return record


def _role(person_key: str, organization_id) -> ProfessionalRoleClaim:
    return ProfessionalRoleClaim(
        claim_key="role:alice:example-security",
        person_key=person_key,
        source_id="organization-site",
        source_record_key="team-page:alice",
        role_title="Chief Information Security Officer",
        team_name="Security",
        observed_at=NOW,
        confidence=0.9,
        processing=_processing(),
        organization_id=organization_id,
        claimed_organization_name="Example Corp",
        organization_link_status=OrganizationLinkStatus.EXACT,
        source_url="https://example.org/team/alice",
        review_state=ProfessionalReviewState.CONFIRMED,
    )


def _reporting(person_key: str, organization_id) -> ReportingLineClaim:
    return ReportingLineClaim(
        claim_key="reporting:alice:bob",
        subject_person_key=person_key,
        manager_person_key="professional-person:manager-bob",
        source_id="organization-site",
        source_record_key="team-page:reporting",
        source_url="https://example.org/team",
        observed_at=NOW,
        confidence=0.7,
        processing=_processing(),
        organization_id=organization_id,
        review_state=ProfessionalReviewState.CONFIRMED,
    )


def _contact(person_key: str, organization_id) -> ProfessionalContactEvidence:
    return ProfessionalContactEvidence(
        contact_key="contact:alice:business-email",
        channel_type=ContactChannelType.BUSINESS_EMAIL,
        evidence_scope=ContactEvidenceScope.ORGANIZATION_PUBLISHED,
        value=RAW_EMAIL,
        source_id="organization-site",
        source_record_key="contact-page:alice",
        source_url="https://example.org/contact/alice",
        observed_at=NOW,
        confidence=0.9,
        processing=_processing(),
        organization_id=organization_id,
        person_key=person_key,
        review_state=ProfessionalReviewState.CONFIRMED,
    )


def _community(person_key: str, organization_id) -> PublicCommunityContext:
    return PublicCommunityContext(
        context_key="community:alice:event",
        community_name="Security Association",
        context_type="public_event_speaker",
        context_value="Annual security conference",
        acquisition_mode=CommunityAcquisitionMode.AUTHORIZED_EXPORT,
        authorization_reference="approval:community-export-2026-08",
        source_id="authorized-community-export",
        source_record_key="speaker:alice",
        source_url="https://community.example/event",
        observed_at=NOW,
        confidence=0.8,
        processing=_processing(),
        organization_id=organization_id,
        person_key=person_key,
        review_state=ProfessionalReviewState.CONFIRMED,
    )

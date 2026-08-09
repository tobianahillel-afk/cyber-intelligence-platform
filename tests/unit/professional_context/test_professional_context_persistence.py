from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select

from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.professional_context.domain import (
    ContactChannelType,
    ContactEvidenceScope,
    LawfulBasis,
    OrganizationLinkStatus,
    ProfessionalClaimType,
    ProfessionalContactEvidence,
    ProfessionalPersonReference,
    ProfessionalProcessingContext,
    ProfessionalReviewState,
    ProfessionalRoleClaim,
    source_person_key,
)
from cip.modules.professional_context.infrastructure.contact_models import (
    ProfessionalContactSnapshotRecord,
)
from cip.modules.professional_context.infrastructure.contact_persistence import (
    persist_professional_contacts,
)
from cip.modules.professional_context.infrastructure.person_models import (
    ProfessionalPersonSnapshotRecord,
)
from cip.modules.professional_context.infrastructure.person_persistence import (
    persist_professional_people,
)
from cip.modules.professional_context.infrastructure.role_models import (
    ProfessionalRoleSnapshotRecord,
)
from cip.modules.professional_context.infrastructure.role_persistence import (
    persist_professional_roles,
)
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)


def test_person_replay_is_idempotent() -> None:
    session = _session()
    reference = _person_reference()

    first = persist_professional_people(session, (reference,), now=NOW)
    second = persist_professional_people(session, (reference,), now=NOW)
    snapshots = session.scalar(select(func.count()).select_from(ProfessionalPersonSnapshotRecord))

    assert first[0].id == second[0].id
    assert snapshots == 1
    assert first[0].display_name == "Alice Martin"


def test_role_correction_updates_current_and_preserves_two_snapshots() -> None:
    session = _session()
    organization = _organization(session)
    person_key = _person_reference().person_key
    original = _role(
        person_key=person_key,
        organization_id=organization.id,
        source_record_key="role-v1",
        role_title="Security Manager",
        observed_at=NOW - timedelta(days=2),
    )
    corrected = _role(
        person_key=person_key,
        organization_id=organization.id,
        source_record_key="role-v2",
        role_title="Chief Information Security Officer",
        observed_at=NOW - timedelta(days=1),
        claim_type=ProfessionalClaimType.CORRECTION,
        supersedes_record_key="role-v1",
    )

    persist_professional_roles(session, (original,), now=NOW)
    records = persist_professional_roles(session, (corrected,), now=NOW)
    snapshots = tuple(
        session.scalars(
            select(ProfessionalRoleSnapshotRecord).order_by(
                ProfessionalRoleSnapshotRecord.observed_at
            )
        )
    )

    assert records[0].role_title == "Chief Information Security Officer"
    assert records[0].evidence_count == 1
    assert len(snapshots) == 2
    assert snapshots[0].role_title == "Security Manager"
    assert snapshots[1].role_title == "Chief Information Security Officer"


def test_contact_replay_uses_snapshot_digest() -> None:
    session = _session()
    contact = ProfessionalContactEvidence(
        contact_key="contact:alice:business-email",
        channel_type=ContactChannelType.BUSINESS_EMAIL,
        evidence_scope=ContactEvidenceScope.ORGANIZATION_PUBLISHED,
        value="alice@example.org",
        source_id="organization-site",
        source_record_key="contact-page:alice",
        source_url="https://example.org/contact",
        observed_at=NOW,
        confidence=0.9,
        processing=_processing(),
        person_key="professional-person:alice",
        review_state=ProfessionalReviewState.CONFIRMED,
    )

    first = persist_professional_contacts(session, (contact,), now=NOW)
    second = persist_professional_contacts(session, (contact,), now=NOW)
    snapshots = session.scalar(
        select(func.count()).select_from(ProfessionalContactSnapshotRecord)
    )

    assert first[0].id == second[0].id
    assert snapshots == 1
    assert first[0].value == "alice@example.org"


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


def _person_reference() -> ProfessionalPersonReference:
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


def _role(
    *,
    person_key: str,
    organization_id,
    source_record_key: str,
    role_title: str,
    observed_at: datetime,
    claim_type: ProfessionalClaimType = ProfessionalClaimType.ASSERTION,
    supersedes_record_key: str | None = None,
) -> ProfessionalRoleClaim:
    return ProfessionalRoleClaim(
        claim_key="role:alice:example-security",
        person_key=person_key,
        source_id="organization-site",
        source_record_key=source_record_key,
        role_title=role_title,
        observed_at=observed_at,
        confidence=0.9,
        processing=_processing(),
        organization_id=organization_id,
        claimed_organization_name="Example Corp",
        organization_link_status=OrganizationLinkStatus.EXACT,
        review_state=ProfessionalReviewState.CONFIRMED,
        claim_type=claim_type,
        supersedes_record_key=supersedes_record_key,
    )

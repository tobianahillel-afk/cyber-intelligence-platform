from __future__ import annotations

from datetime import datetime

from cip.modules.organizations.infrastructure.persistence_time import coerce_utc
from cip.modules.professional_context.domain import (
    CommunityAcquisitionMode,
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
    PublicCommunityContext,
    ReportingLineClaim,
)
from cip.modules.professional_context.infrastructure.contact_models import (
    ProfessionalContactSnapshotRecord,
)
from cip.modules.professional_context.infrastructure.context_models import (
    ProfessionalCommunitySnapshotRecord,
)
from cip.modules.professional_context.infrastructure.person_models import (
    ProfessionalPersonSnapshotRecord,
)
from cip.modules.professional_context.infrastructure.role_models import (
    ProfessionalReportingSnapshotRecord,
    ProfessionalRoleSnapshotRecord,
)

ProcessingRow = (
    ProfessionalPersonSnapshotRecord
    | ProfessionalRoleSnapshotRecord
    | ProfessionalReportingSnapshotRecord
    | ProfessionalContactSnapshotRecord
    | ProfessionalCommunitySnapshotRecord
)


def person_snapshot(record: ProfessionalPersonSnapshotRecord) -> ProfessionalPersonReference:
    return ProfessionalPersonReference(
        person_key=record.person_key,
        display_name=record.display_name,
        source_id=record.source_id,
        source_kind=record.source_kind,
        source_record_key=record.source_record_key,
        source_url=record.source_url,
        observed_at=coerce_utc(record.observed_at),
        confidence=record.confidence,
        processing=_processing(record),
        review_state=ProfessionalReviewState(record.review_state),
        active=record.active,
        suppressed=record.suppressed,
        deleted=record.deleted,
    )


def role_snapshot(record: ProfessionalRoleSnapshotRecord) -> ProfessionalRoleClaim:
    return ProfessionalRoleClaim(
        claim_key=record.claim_key,
        person_key=record.person_key,
        source_id=record.source_id,
        source_record_key=record.source_record_key,
        source_url=record.source_url,
        role_title=record.role_title,
        team_name=record.team_name,
        organization_id=record.organization_id,
        claimed_organization_name=record.claimed_organization_name,
        organization_link_status=OrganizationLinkStatus(record.organization_link_status),
        claim_type=ProfessionalClaimType(record.claim_type),
        review_state=ProfessionalReviewState(record.review_state),
        observed_at=coerce_utc(record.observed_at),
        valid_from=_optional_time(record.valid_from),
        valid_until=_optional_time(record.valid_until),
        expires_at=_optional_time(record.expires_at),
        confidence=record.confidence,
        processing=_processing(record),
        active=record.active,
        historical_only=record.historical_only,
        suppressed=record.suppressed,
        deleted=record.deleted,
        supersedes_record_key=record.supersedes_record_key,
    )


def reporting_snapshot(record: ProfessionalReportingSnapshotRecord) -> ReportingLineClaim:
    return ReportingLineClaim(
        claim_key=record.claim_key,
        subject_person_key=record.subject_person_key,
        manager_person_key=record.manager_person_key,
        organization_id=record.organization_id,
        source_id=record.source_id,
        source_record_key=record.source_record_key,
        source_url=record.source_url,
        claim_type=ProfessionalClaimType(record.claim_type),
        review_state=ProfessionalReviewState(record.review_state),
        observed_at=coerce_utc(record.observed_at),
        valid_from=_optional_time(record.valid_from),
        valid_until=_optional_time(record.valid_until),
        confidence=record.confidence,
        processing=_processing(record),
        active=record.active,
        suppressed=record.suppressed,
        deleted=record.deleted,
        supersedes_record_key=record.supersedes_record_key,
    )


def contact_snapshot(record: ProfessionalContactSnapshotRecord) -> ProfessionalContactEvidence:
    return ProfessionalContactEvidence(
        contact_key=record.contact_key,
        channel_type=ContactChannelType(record.channel_type),
        evidence_scope=ContactEvidenceScope(record.evidence_scope),
        value=record.value,
        organization_id=record.organization_id,
        person_key=record.person_key,
        source_id=record.source_id,
        source_record_key=record.source_record_key,
        source_url=record.source_url,
        claim_type=ProfessionalClaimType(record.claim_type),
        review_state=ProfessionalReviewState(record.review_state),
        observed_at=coerce_utc(record.observed_at),
        confidence=record.confidence,
        processing=_processing(record),
        active=record.active,
        suppressed=record.suppressed,
        deleted=record.deleted,
        supersedes_record_key=record.supersedes_record_key,
    )


def community_snapshot(record: ProfessionalCommunitySnapshotRecord) -> PublicCommunityContext:
    return PublicCommunityContext(
        context_key=record.context_key,
        community_name=record.community_name,
        context_type=record.context_type,
        context_value=record.context_value,
        acquisition_mode=CommunityAcquisitionMode(record.acquisition_mode),
        authorization_reference=record.authorization_reference,
        organization_id=record.organization_id,
        person_key=record.person_key,
        source_id=record.source_id,
        source_record_key=record.source_record_key,
        source_url=record.source_url,
        claim_type=ProfessionalClaimType(record.claim_type),
        review_state=ProfessionalReviewState(record.review_state),
        observed_at=coerce_utc(record.observed_at),
        confidence=record.confidence,
        processing=_processing(record),
        active=record.active,
        suppressed=record.suppressed,
        deleted=record.deleted,
        metadata_only=record.metadata_only,
        supersedes_record_key=record.supersedes_record_key,
    )


def _processing(record: ProcessingRow) -> ProfessionalProcessingContext:
    return ProfessionalProcessingContext(
        lawful_basis=LawfulBasis(record.lawful_basis),
        lawful_basis_reference=record.lawful_basis_reference,
        purpose=record.processing_purpose,
        reviewed_at=coerce_utc(record.processing_reviewed_at),
        retention_until=coerce_utc(record.retention_until),
    )


def _optional_time(value: datetime | None) -> datetime | None:
    return coerce_utc(value) if value is not None else None

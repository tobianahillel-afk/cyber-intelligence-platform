from __future__ import annotations

from uuid import UUID

from cip.adapters.sources.incident_catalogs.schemas import (
    OfficialDisclosureKind,
    OfficialIncidentDisclosure,
    OrganizationReference,
    PublicIncidentKind,
    PublicIncidentReport,
    RansomwareMetadataRecord,
    ReportKind,
)
from cip.modules.incident_intelligence.domain.models import (
    IncidentClaimSnapshot,
    IncidentClaimType,
    IncidentSourceKind,
    IncidentType,
    OrganizationLinkStatus,
)


def map_official_disclosure(
    record: OfficialIncidentDisclosure,
    *,
    source_id: str,
) -> IncidentClaimSnapshot:
    organization_id, link_status = _organization_link(record.organization)
    claim_type = IncidentClaimType(record.disclosure_kind.value)
    return IncidentClaimSnapshot(
        source_id=source_id,
        source_kind=_official_source_kind(record.disclosure_kind),
        source_record_key=record.record_id,
        source_url=record.source_url,
        incident_key=record.incident_key,
        claim_type=claim_type,
        incident_type=_incident_type(record.incident_kind),
        title=record.title,
        summary=record.summary,
        claimed_organization_name=(
            record.organization.claimed_name
            if record.organization
            else None
        ),
        organization_id=organization_id,
        organization_link_status=link_status,
        published_at=record.published_at,
        modified_at=record.modified_at,
        occurrence_start_at=record.occurrence_start_at,
        occurrence_end_at=record.occurrence_end_at,
        discovered_at=record.discovered_at,
        confirmed_at=record.confirmed_at,
        independence_key=source_id,
        confidence=1.0,
        active=True,
        historical_only=record.historical_only,
        metadata_only=True,
        supersedes_record_key=record.supersedes_record_id,
    )


def map_public_report(
    record: PublicIncidentReport,
    *,
    source_id: str,
) -> IncidentClaimSnapshot:
    organization_id, link_status = _organization_link(record.organization)
    return IncidentClaimSnapshot(
        source_id=source_id,
        source_kind=_report_source_kind(record.report_kind),
        source_record_key=record.record_id,
        source_url=record.source_url,
        incident_key=record.incident_key,
        claim_type=IncidentClaimType(record.report_kind.value),
        incident_type=_incident_type(record.incident_kind),
        title=record.title,
        summary=record.summary,
        claimed_organization_name=(
            record.organization.claimed_name
            if record.organization
            else None
        ),
        organization_id=organization_id,
        organization_link_status=link_status,
        published_at=record.published_at,
        modified_at=record.modified_at,
        occurrence_start_at=record.occurrence_start_at,
        occurrence_end_at=record.occurrence_end_at,
        discovered_at=record.discovered_at,
        independence_key=record.syndication_group or source_id,
        confidence=record.confidence,
        active=True,
        historical_only=record.historical_only,
        metadata_only=True,
    )


def map_ransomware_metadata(
    record: RansomwareMetadataRecord,
    *,
    source_id: str,
) -> IncidentClaimSnapshot:
    return IncidentClaimSnapshot(
        source_id=source_id,
        source_kind=IncidentSourceKind.RANSOMWARE_METADATA,
        source_record_key=record.record_id,
        source_url=record.provider_record_url,
        incident_key=record.incident_key,
        claim_type=IncidentClaimType.ATTACKER_ALLEGATION,
        incident_type=IncidentType.RANSOMWARE,
        title=record.claim_title,
        summary=record.claim_summary,
        claimed_organization_name=record.claimed_victim_name,
        organization_id=None,
        organization_link_status=OrganizationLinkStatus.REVIEW_REQUIRED,
        published_at=record.published_at,
        modified_at=record.modified_at,
        occurrence_start_at=record.occurrence_start_at,
        independence_key=record.syndication_group or source_id,
        confidence=0.35,
        active=True,
        historical_only=record.historical_only,
        metadata_only=True,
    )


def _organization_link(
    reference: OrganizationReference | None,
) -> tuple[UUID | None, OrganizationLinkStatus]:
    if reference is None:
        return None, OrganizationLinkStatus.UNRESOLVED
    if reference.exact_organization_id is not None:
        try:
            organization_id = UUID(reference.exact_organization_id)
        except ValueError as exc:
            raise ValueError("exact_organization_id must be a UUID") from exc
        return organization_id, OrganizationLinkStatus.EXACT
    if reference.exact_registration_id is not None:
        return None, OrganizationLinkStatus.REVIEW_REQUIRED
    return None, OrganizationLinkStatus.CANDIDATE


def _official_source_kind(
    kind: OfficialDisclosureKind,
) -> IncidentSourceKind:
    if kind is OfficialDisclosureKind.REGULATOR_NOTICE:
        return IncidentSourceKind.REGULATOR
    if kind is OfficialDisclosureKind.CERT_NOTICE:
        return IncidentSourceKind.CERT
    return IncidentSourceKind.COMPANY


def _report_source_kind(kind: ReportKind) -> IncidentSourceKind:
    if kind is ReportKind.MEDIA_REPORT:
        return IncidentSourceKind.MEDIA
    if kind is ReportKind.RESEARCHER_REPORT:
        return IncidentSourceKind.RESEARCH
    return IncidentSourceKind.PROVIDER


def _incident_type(kind: PublicIncidentKind) -> IncidentType:
    return IncidentType(kind.value)

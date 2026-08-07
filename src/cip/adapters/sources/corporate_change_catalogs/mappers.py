from __future__ import annotations

from uuid import UUID

from cip.adapters.sources.corporate_change_catalogs.schemas import (
    OfficialChangeDisclosure,
    OrganizationReference,
    PublicChangeReport,
)
from cip.modules.corporate_changes.domain.models import (
    ChangeClaimSnapshot,
    ChangeClaimType,
    ChangeEventType,
    ChangeSourceKind,
    OrganizationLinkStatus,
)


def map_official_change(
    record: OfficialChangeDisclosure,
    *,
    source_id: str,
    source_kind: ChangeSourceKind,
) -> ChangeClaimSnapshot:
    if source_kind not in {
        ChangeSourceKind.OFFICIAL_FILING,
        ChangeSourceKind.REGULATOR,
        ChangeSourceKind.COMPANY,
    }:
        raise ValueError("official changes require an official source kind")
    organization_id, link_status = _organization_link(record.organization)
    return ChangeClaimSnapshot(
        source_id=source_id,
        source_kind=source_kind,
        source_record_key=record.record_id,
        article_id=record.article_id,
        source_url=record.source_url,
        event_key=record.event_key,
        claim_type=ChangeClaimType(record.disclosure_kind.value),
        event_type=ChangeEventType(record.change_kind.value),
        title=record.title,
        excerpt=record.excerpt,
        claimed_organization_name=(
            record.organization.claimed_name if record.organization else None
        ),
        organization_id=organization_id,
        organization_link_status=link_status,
        published_at=record.published_at,
        modified_at=record.modified_at,
        event_at=record.event_at,
        expires_at=record.expires_at,
        independence_key=source_id,
        confidence=1.0,
        active=True,
        historical_only=record.historical_only,
        metadata_only=True,
        supersedes_record_key=record.supersedes_record_id,
    )


def map_public_change_report(
    record: PublicChangeReport,
    *,
    source_id: str,
) -> ChangeClaimSnapshot:
    organization_id, link_status = _organization_link(record.organization)
    source_kind = (
        ChangeSourceKind.MEDIA
        if record.source_class == "media"
        else ChangeSourceKind.ANALYST
    )
    return ChangeClaimSnapshot(
        source_id=source_id,
        source_kind=source_kind,
        source_record_key=record.record_id,
        article_id=record.article_id,
        source_url=record.source_url,
        event_key=record.event_key,
        claim_type=ChangeClaimType(record.report_kind.value),
        event_type=ChangeEventType(record.change_kind.value),
        title=record.title,
        excerpt=record.excerpt,
        claimed_organization_name=(
            record.organization.claimed_name if record.organization else None
        ),
        organization_id=organization_id,
        organization_link_status=link_status,
        published_at=record.published_at,
        modified_at=record.modified_at,
        event_at=record.event_at,
        expires_at=record.expires_at,
        independence_key=source_id,
        syndication_group_key=record.syndication_group,
        confidence=record.confidence,
        active=True,
        historical_only=record.historical_only,
        metadata_only=True,
        supersedes_record_key=record.supersedes_record_id,
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
    if reference.registration_id is not None:
        return None, OrganizationLinkStatus.REVIEW_REQUIRED
    return None, OrganizationLinkStatus.CANDIDATE

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from cip.adapters.sources.incident_catalogs.mappers import (
    map_official_disclosure,
    map_public_report,
    map_ransomware_metadata,
)
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
    IncidentClaimType,
    IncidentSourceKind,
    OrganizationLinkStatus,
)

NOW = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)


def test_official_disclosure_maps_exact_identity_and_confirmation() -> None:
    organization_id = uuid4()
    record = OfficialIncidentDisclosure(
        record_id="statement-1",
        incident_key="incident:example:1",
        source_url="https://example.test/security/statement-1",
        disclosure_kind=OfficialDisclosureKind.COMPANY_CONFIRMATION,
        incident_kind=PublicIncidentKind.DATA_BREACH,
        title="Company security incident statement",
        summary="The company confirmed a bounded public incident summary.",
        organization=OrganizationReference(
            claimed_name="Example SA",
            exact_organization_id=str(organization_id),
        ),
        published_at=NOW,
        modified_at=NOW,
        confirmed_at=NOW,
    )

    claim = map_official_disclosure(record, source_id="company-pressroom")

    assert claim.claim_type is IncidentClaimType.COMPANY_CONFIRMATION
    assert claim.source_kind is IncidentSourceKind.COMPANY
    assert claim.organization_id == organization_id
    assert claim.organization_link_status is OrganizationLinkStatus.EXACT
    assert claim.is_official_confirmation is True
    assert claim.confidence == 1.0


def test_public_reports_share_the_declared_syndication_group() -> None:
    record = PublicIncidentReport(
        record_id="wire-1",
        incident_key="incident:example:1",
        source_url="https://media.example/reports/wire-1",
        report_kind=ReportKind.MEDIA_REPORT,
        incident_kind=PublicIncidentKind.RANSOMWARE,
        title="Media report",
        summary="A bounded media report about an alleged incident.",
        organization=OrganizationReference(claimed_name="Example SA"),
        published_at=NOW,
        modified_at=NOW,
        syndication_group="wire-service-story-1",
        confidence=0.65,
    )

    claim = map_public_report(record, source_id="media-feed")

    assert claim.claim_type is IncidentClaimType.MEDIA_REPORT
    assert claim.independence_key == "wire-service-story-1"
    assert claim.organization_id is None
    assert claim.organization_link_status is OrganizationLinkStatus.CANDIDATE


def test_ransomware_metadata_remains_a_low_confidence_allegation() -> None:
    record = RansomwareMetadataRecord(
        record_id="provider-record-1",
        incident_key="incident:example:1",
        provider_record_url="https://licensed-provider.example/records/1",
        provider_name="Licensed metadata provider",
        claimed_victim_name="Example SA",
        group_name="Example Group",
        claim_title="Public extortion metadata",
        claim_summary="Provider-published metadata only; no victim content.",
        published_at=NOW,
        modified_at=NOW,
    )

    claim = map_ransomware_metadata(record, source_id="ransomware-provider")

    assert claim.claim_type is IncidentClaimType.ATTACKER_ALLEGATION
    assert claim.source_kind is IncidentSourceKind.RANSOMWARE_METADATA
    assert claim.organization_link_status is OrganizationLinkStatus.REVIEW_REQUIRED
    assert claim.organization_id is None
    assert claim.confidence == 0.35
    assert claim.is_official_confirmation is False


def test_ransomware_schema_rejects_threat_actor_onion_urls() -> None:
    with pytest.raises(ValidationError, match="onion URLs are forbidden"):
        RansomwareMetadataRecord(
            record_id="provider-record-1",
            incident_key="incident:example:1",
            provider_record_url="https://example.onion/records/1",
            provider_name="Forbidden source",
            claimed_victim_name="Example SA",
            claim_title="Forbidden claim",
            claim_summary="This source path must never enter the platform.",
            published_at=NOW,
            modified_at=NOW,
        )


def test_denial_cannot_carry_a_confirmation_timestamp() -> None:
    with pytest.raises(ValidationError, match="official confirmation"):
        OfficialIncidentDisclosure(
            record_id="denial-1",
            incident_key="incident:example:1",
            source_url="https://example.test/security/denial-1",
            disclosure_kind=OfficialDisclosureKind.DENIAL,
            title="Company denial",
            summary="The company denied the public allegation.",
            published_at=NOW,
            modified_at=NOW,
            confirmed_at=NOW,
        )

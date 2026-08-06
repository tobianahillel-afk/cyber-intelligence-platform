from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cip.modules.incident_intelligence.domain.models import (
    IncidentClaimSnapshot,
    IncidentClaimType,
    IncidentSourceKind,
    IncidentStatus,
    IncidentType,
    OrganizationLinkStatus,
)
from cip.modules.incident_intelligence.domain.reconciliation import (
    reconcile_incident_claims,
)

NOW = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)


def test_attacker_allegation_is_not_official_confirmation() -> None:
    incident = reconcile_incident_claims(
        (
            _claim(
                source_id="ransomware-metadata",
                record_key="claim-1",
                claim_type=IncidentClaimType.ATTACKER_ALLEGATION,
                source_kind=IncidentSourceKind.RANSOMWARE_METADATA,
                confidence=0.35,
            ),
        )
    )[0]

    assert incident.status is IncidentStatus.ALLEGED
    assert incident.officially_confirmed is False
    assert incident.confirmed_at is None
    assert incident.independent_source_count == 1
    assert incident.organization_link_status is OrganizationLinkStatus.REVIEW_REQUIRED


def test_syndication_counts_once_before_official_confirmation() -> None:
    first_report = replace(
        _claim(
            source_id="media-a",
            record_key="report-a",
            claim_type=IncidentClaimType.MEDIA_REPORT,
            source_kind=IncidentSourceKind.MEDIA,
        ),
        independence_key="wire-story-42",
    )
    syndicated_report = replace(
        first_report,
        source_id="media-b",
        source_record_key="report-b",
        source_url="https://media-b.example/incidents/report-b",
    )
    confirmation = replace(
        _claim(
            source_id="company-pressroom",
            record_key="statement-1",
            claim_type=IncidentClaimType.COMPANY_CONFIRMATION,
            source_kind=IncidentSourceKind.COMPANY,
            confidence=1.0,
        ),
        confirmed_at=NOW + timedelta(hours=2),
        modified_at=NOW + timedelta(hours=2),
    )

    incident = reconcile_incident_claims(
        (first_report, syndicated_report, confirmation)
    )[0]

    assert incident.status is IncidentStatus.CONFIRMED
    assert incident.officially_confirmed is True
    assert incident.confirmed_at == NOW + timedelta(hours=2)
    assert incident.claim_count == 3
    assert incident.independent_source_count == 2


def test_conflicting_exact_organization_links_require_review() -> None:
    first = replace(
        _claim(
            source_id="regulator-a",
            record_key="notice-a",
            claim_type=IncidentClaimType.REGULATOR_NOTICE,
            source_kind=IncidentSourceKind.REGULATOR,
            confidence=1.0,
        ),
        organization_id=uuid4(),
        organization_link_status=OrganizationLinkStatus.EXACT,
        confirmed_at=NOW,
    )
    second = replace(
        first,
        source_id="cert-b",
        source_kind=IncidentSourceKind.CERT,
        source_record_key="notice-b",
        source_url="https://cert.example/notices/notice-b",
        organization_id=uuid4(),
    )

    incident = reconcile_incident_claims((first, second))[0]

    assert incident.organization_id is None
    assert incident.organization_link_status is OrganizationLinkStatus.REVIEW_REQUIRED
    assert incident.officially_confirmed is True


def test_later_retraction_replaces_the_current_source_revision() -> None:
    original = _claim(
        source_id="research-feed",
        record_key="record-1",
        claim_type=IncidentClaimType.RESEARCHER_REPORT,
        source_kind=IncidentSourceKind.RESEARCH,
    )
    retraction = replace(
        original,
        claim_type=IncidentClaimType.RETRACTION,
        title="Research report retracted",
        summary="The publisher retracted the original incident report.",
        modified_at=NOW + timedelta(days=1),
        supersedes_record_key="record-1",
    )

    incident = reconcile_incident_claims((original, retraction))[0]

    assert incident.status is IncidentStatus.RETRACTED
    assert incident.has_retraction is True
    assert incident.claim_count == 1
    assert incident.independent_source_count == 0


def test_incident_snapshots_reject_non_metadata_payloads() -> None:
    with pytest.raises(ValueError, match="metadata only"):
        replace(
            _claim(
                source_id="provider",
                record_key="record-1",
                claim_type=IncidentClaimType.PROVIDER_STATEMENT,
                source_kind=IncidentSourceKind.PROVIDER,
            ),
            metadata_only=False,
        )


def test_non_official_claim_cannot_set_confirmation_time() -> None:
    with pytest.raises(ValueError, match="official confirmation"):
        replace(
            _claim(
                source_id="media",
                record_key="record-1",
                claim_type=IncidentClaimType.MEDIA_REPORT,
                source_kind=IncidentSourceKind.MEDIA,
            ),
            confirmed_at=NOW,
        )


def _claim(
    *,
    source_id: str,
    record_key: str,
    claim_type: IncidentClaimType,
    source_kind: IncidentSourceKind,
    confidence: float = 0.7,
) -> IncidentClaimSnapshot:
    return IncidentClaimSnapshot(
        source_id=source_id,
        source_kind=source_kind,
        source_record_key=record_key,
        source_url=f"https://{source_id}.example/incidents/{record_key}",
        incident_key="incident:example:2026-08-06",
        claim_type=claim_type,
        incident_type=IncidentType.RANSOMWARE,
        title="Example public incident claim",
        summary="Bounded public metadata describing the incident claim.",
        claimed_organization_name="Example SA",
        organization_id=None,
        organization_link_status=OrganizationLinkStatus.REVIEW_REQUIRED,
        published_at=NOW,
        modified_at=NOW,
        occurrence_start_at=NOW - timedelta(hours=1),
        discovered_at=NOW,
        confidence=confidence,
        metadata_only=True,
    )

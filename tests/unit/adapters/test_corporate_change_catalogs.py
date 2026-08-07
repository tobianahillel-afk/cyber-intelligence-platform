from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from cip.adapters.sources.corporate_change_catalogs.mappers import (
    map_official_change,
    map_public_change_report,
)
from cip.adapters.sources.corporate_change_catalogs.schemas import (
    OfficialChangeDisclosure,
    OfficialChangeKind,
    OrganizationReference,
    ProviderChangeKind,
    PublicChangeReport,
    ReportChangeKind,
)
from cip.modules.corporate_changes.domain.models import (
    ChangeClaimType,
    ChangeSourceKind,
    OrganizationLinkStatus,
)

NOW = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)


def test_official_disclosure_maps_to_exact_confirmation() -> None:
    organization_id = uuid4()
    record = OfficialChangeDisclosure(
        record_id="filing-1",
        article_id="filing-1",
        event_key="org:funding:2026",
        source_url="https://filings.example.com/filing-1",
        change_kind=ProviderChangeKind.FUNDING,
        disclosure_kind=OfficialChangeKind.CONFIRMATION,
        title="Example Company announces funding",
        excerpt="Official filing metadata confirms the transaction.",
        organization=OrganizationReference(
            claimed_name="Example Company",
            exact_organization_id=str(organization_id),
        ),
        published_at=NOW,
        modified_at=NOW,
    )

    claim = map_official_change(
        record,
        source_id="official-corporate-disclosures",
        source_kind=ChangeSourceKind.OFFICIAL_FILING,
    )

    assert claim.claim_type is ChangeClaimType.CONFIRMATION
    assert claim.organization_id == organization_id
    assert claim.organization_link_status is OrganizationLinkStatus.EXACT
    assert claim.is_official_confirmation is True


def test_public_report_preserves_syndication_and_speculation() -> None:
    record = PublicChangeReport(
        record_id="story-1",
        article_id="story-1",
        event_key="org:acquisition:2026",
        source_url="https://media.example.com/story-1",
        source_class="media",
        change_kind=ProviderChangeKind.ACQUISITION,
        report_kind=ReportChangeKind.SPECULATION,
        title="Market report discusses possible acquisition",
        excerpt="The article reports unconfirmed market speculation.",
        organization=OrganizationReference(claimed_name="Example Company"),
        published_at=NOW,
        modified_at=NOW,
        syndication_group="wire-42",
        confidence=0.45,
    )

    claim = map_public_change_report(
        record,
        source_id="licensed-corporate-news-metadata",
    )

    assert claim.claim_type is ChangeClaimType.SPECULATION
    assert claim.source_kind is ChangeSourceKind.MEDIA
    assert claim.syndication_group_key == "wire-42"
    assert claim.organization_link_status is OrganizationLinkStatus.CANDIDATE
    assert claim.is_official_confirmation is False


def test_official_mapper_rejects_non_official_source_kind() -> None:
    record = OfficialChangeDisclosure(
        record_id="company-1",
        article_id="company-1",
        event_key="org:security:2026",
        source_url="https://company.example.com/update",
        change_kind=ProviderChangeKind.SECURITY_COMMITMENT,
        disclosure_kind=OfficialChangeKind.CONFIRMATION,
        title="Security commitment",
        excerpt="The company announces a public security commitment.",
        published_at=NOW,
        modified_at=NOW,
    )

    with pytest.raises(ValueError, match="official source kind"):
        map_official_change(
            record,
            source_id="company",
            source_kind=ChangeSourceKind.MEDIA,
        )


def test_provider_schema_rejects_overlong_excerpt() -> None:
    with pytest.raises(ValueError):
        PublicChangeReport(
            record_id="story-1",
            article_id="story-1",
            event_key="org:change:2026",
            source_url="https://media.example.com/story-1",
            source_class="analyst",
            change_kind=ProviderChangeKind.OTHER,
            report_kind=ReportChangeKind.REPORT,
            title="Change",
            excerpt="x" * 501,
            published_at=NOW,
            modified_at=NOW,
        )

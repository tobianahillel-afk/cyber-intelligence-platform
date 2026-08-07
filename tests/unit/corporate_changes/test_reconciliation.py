from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cip.modules.corporate_changes.domain.models import (
    MAX_EXCERPT_LENGTH,
    ChangeClaimSnapshot,
    ChangeClaimType,
    ChangeEventStatus,
    ChangeEventType,
    ChangeSourceKind,
    OrganizationLinkStatus,
)
from cip.modules.corporate_changes.domain.reconciliation import reconcile_change_claims

NOW = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)


def test_official_company_confirmation_is_confirmed() -> None:
    claim = _claim(
        source_id="company",
        source_kind=ChangeSourceKind.COMPANY,
        claim_type=ChangeClaimType.CONFIRMATION,
    )

    event = reconcile_change_claims((claim,), now=NOW)[0]

    assert event.status is ChangeEventStatus.CONFIRMED
    assert event.officially_confirmed is True
    assert event.independent_source_count == 1


def test_media_speculation_is_not_confirmation() -> None:
    claim = _claim(
        source_id="media-a",
        source_kind=ChangeSourceKind.MEDIA,
        claim_type=ChangeClaimType.SPECULATION,
    )

    event = reconcile_change_claims((claim,), now=NOW)[0]

    assert event.status is ChangeEventStatus.SPECULATIVE
    assert event.officially_confirmed is False


def test_syndicated_reports_count_as_one_independent_source() -> None:
    first = _claim(
        source_id="wire-a",
        source_kind=ChangeSourceKind.MEDIA,
        claim_type=ChangeClaimType.REPORT,
        syndication_group_key="wire-story-42",
    )
    second = replace(
        first,
        source_id="republisher-b",
        source_record_key="story-b",
        article_id="article-b",
        source_url="https://news-b.example.com/story-b",
    )

    event = reconcile_change_claims((first, second), now=NOW)[0]

    assert event.status is ChangeEventStatus.REPORTED
    assert event.claim_count == 2
    assert event.independent_source_count == 1


def test_distinct_reports_count_as_independent_sources() -> None:
    first = _claim(
        source_id="media-a",
        source_kind=ChangeSourceKind.MEDIA,
        claim_type=ChangeClaimType.REPORT,
    )
    second = replace(
        first,
        source_id="media-b",
        source_record_key="story-b",
        article_id="article-b",
        source_url="https://news-b.example.com/story-b",
        independence_key="media-b",
    )

    event = reconcile_change_claims((first, second), now=NOW)[0]

    assert event.independent_source_count == 2


def test_superseding_retraction_replaces_old_confirmation() -> None:
    confirmation = _claim(
        source_id="company",
        source_kind=ChangeSourceKind.COMPANY,
        claim_type=ChangeClaimType.CONFIRMATION,
    )
    retraction = replace(
        confirmation,
        source_record_key="record-r2",
        article_id="article-r2",
        claim_type=ChangeClaimType.RETRACTION,
        modified_at=NOW + timedelta(hours=1),
        supersedes_record_key=confirmation.source_record_key,
    )

    event = reconcile_change_claims((confirmation, retraction), now=NOW)[0]

    assert event.status is ChangeEventStatus.RETRACTED
    assert event.officially_confirmed is False
    assert event.claim_count == 1
    assert event.has_retraction is True


def test_expired_report_becomes_stale() -> None:
    claim = _claim(
        source_id="media-a",
        source_kind=ChangeSourceKind.MEDIA,
        claim_type=ChangeClaimType.REPORT,
        expires_at=NOW - timedelta(minutes=1),
        published_at=NOW - timedelta(days=2),
        modified_at=NOW - timedelta(days=1),
    )

    event = reconcile_change_claims((claim,), now=NOW)[0]

    assert event.status is ChangeEventStatus.STALE


def test_conflicting_exact_organization_links_require_review() -> None:
    first = _claim(
        source_id="company-a",
        source_kind=ChangeSourceKind.COMPANY,
        claim_type=ChangeClaimType.CONFIRMATION,
        organization_id=uuid4(),
        organization_link_status=OrganizationLinkStatus.EXACT,
    )
    second = replace(
        first,
        source_id="regulator-b",
        source_record_key="record-b",
        article_id="article-b",
        source_url="https://regulator.example.com/notice-b",
        organization_id=uuid4(),
        independence_key="regulator-b",
    )

    event = reconcile_change_claims((first, second), now=NOW)[0]

    assert event.organization_id is None
    assert event.organization_link_status is OrganizationLinkStatus.REVIEW_REQUIRED


def test_event_time_stays_separate_from_publication_time() -> None:
    event_at = NOW - timedelta(days=30)
    claim = _claim(
        source_id="filing",
        source_kind=ChangeSourceKind.OFFICIAL_FILING,
        claim_type=ChangeClaimType.CONFIRMATION,
        event_at=event_at,
    )

    event = reconcile_change_claims((claim,), now=NOW)[0]

    assert event.event_at == event_at
    assert event.first_published_at == NOW - timedelta(hours=2)


def test_excerpt_is_bounded() -> None:
    with pytest.raises(ValueError, match="excerpt"):
        _claim(
            source_id="media-a",
            source_kind=ChangeSourceKind.MEDIA,
            claim_type=ChangeClaimType.REPORT,
            excerpt="x" * (MAX_EXCERPT_LENGTH + 1),
        )


def test_exact_link_requires_organization_id() -> None:
    with pytest.raises(ValueError, match="exact organization links"):
        _claim(
            source_id="company",
            source_kind=ChangeSourceKind.COMPANY,
            claim_type=ChangeClaimType.CONFIRMATION,
            organization_link_status=OrganizationLinkStatus.EXACT,
        )


def _claim(
    *,
    source_id: str,
    source_kind: ChangeSourceKind,
    claim_type: ChangeClaimType,
    source_record_key: str = "record-a",
    article_id: str = "article-a",
    source_url: str = "https://news.example.com/story-a",
    excerpt: str = "Example public change metadata.",
    event_at: datetime | None = None,
    expires_at: datetime | None = None,
    published_at: datetime | None = None,
    modified_at: datetime | None = None,
    syndication_group_key: str | None = None,
    organization_id: object | None = None,
    organization_link_status: OrganizationLinkStatus = OrganizationLinkStatus.CANDIDATE,
) -> ChangeClaimSnapshot:
    resolved_id = organization_id if hasattr(organization_id, "hex") else None
    return ChangeClaimSnapshot(
        source_id=source_id,
        source_kind=source_kind,
        source_record_key=source_record_key,
        article_id=article_id,
        source_url=source_url,
        event_key="example-company:cloud-program:2026",
        claim_type=claim_type,
        event_type=ChangeEventType.CLOUD_DIGITAL_PROGRAM,
        title="Example company announces a digital program",
        excerpt=excerpt,
        claimed_organization_name="Example Company",
        organization_id=resolved_id,
        organization_link_status=organization_link_status,
        published_at=published_at or NOW - timedelta(hours=2),
        modified_at=modified_at or NOW - timedelta(hours=1),
        event_at=event_at,
        expires_at=expires_at,
        independence_key=source_id,
        syndication_group_key=syndication_group_key,
        confidence=0.8,
    )

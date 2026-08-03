import pytest
from pydantic import ValidationError

from cip.compliance.source_policy import SourcePolicy, SourceStatus, SourceType


def test_allowed_api_policy_permits_declared_category() -> None:
    policy = SourcePolicy(
        id="official-feed",
        name="Official Feed",
        base_url="https://example.org",
        status=SourceStatus.ALLOWED,
        source_type=SourceType.API,
        owner="Example Authority",
        terms_url="https://example.org/terms",
        allowed_data_categories={"public_incident_metadata"},
        prohibited_data_categories={"credentials", "victim_files"},
        rate_limit_per_minute=30,
    )

    assert policy.permits("public_incident_metadata") is True
    assert policy.permits("credentials") is False
    assert policy.permits("unknown_category") is False


def test_manual_source_cannot_be_automated() -> None:
    policy = SourcePolicy(
        id="manual-review",
        name="Manual analyst review",
        base_url="https://example.org",
        status=SourceStatus.CONDITIONAL,
        source_type=SourceType.MANUAL,
        owner="Example Publisher",
        allowed_data_categories={"public_report_metadata"},
    )

    assert policy.permits("public_report_metadata", automated=True) is False
    assert policy.permits("public_report_metadata", automated=False) is True


def test_overlapping_categories_are_rejected() -> None:
    with pytest.raises(ValidationError, match="both allowed and prohibited"):
        SourcePolicy(
            id="invalid-source",
            name="Invalid",
            base_url="https://example.org",
            status=SourceStatus.ALLOWED,
            source_type=SourceType.FEED,
            owner="Example",
            licence="CC-BY-4.0",
            allowed_data_categories={"credentials"},
            prohibited_data_categories={"credentials"},
        )


def test_blocked_source_cannot_allow_categories() -> None:
    with pytest.raises(ValidationError, match="blocked sources"):
        SourcePolicy(
            id="blocked-source",
            name="Blocked",
            base_url="https://example.org",
            status=SourceStatus.BLOCKED,
            source_type=SourceType.WEBSITE,
            owner="Example",
            allowed_data_categories={"public_incident_metadata"},
        )

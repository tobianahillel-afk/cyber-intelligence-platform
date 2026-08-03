from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from cip.modules.data_governance.domain.retention import RetentionPolicy, RetentionRule
from cip.modules.data_governance.domain.suppression import (
    SuppressionChannel,
    SuppressionEntry,
    SuppressionReason,
    create_suppression,
    hash_identifier,
    normalize_identifier,
)
from cip.modules.data_governance.infrastructure.retention_loader import load_retention_policy
from cip.modules.source_governance.domain.models import DataCategory

NOW = datetime(2026, 8, 3, 16, 0, tzinfo=UTC)
PEPPER = b"test-only-pepper"


def test_repository_retention_policy_loads_and_calculates_deadlines() -> None:
    policy = load_retention_policy(Path("policies/retention.yml"))

    assert policy.version == 1
    assert policy.retention_deadline(DataCategory.PROFESSIONAL_CONTACT, NOW) == NOW + timedelta(
        days=1095
    )
    assert policy.review_deadline(DataCategory.PUBLIC_TENDER, NOW) == NOW + timedelta(days=365)
    assert policy.restoration_requires_suppressions is True


def test_prohibited_category_has_no_retention_deadline() -> None:
    policy = load_retention_policy(Path("policies/retention.yml"))

    with pytest.raises(ValueError, match="prohibited"):
        policy.retention_deadline(DataCategory.CREDENTIAL, NOW)


def test_missing_rule_is_reported() -> None:
    policy = RetentionPolicy(
        version=1,
        rules={},
        prohibited_categories=frozenset(),
        suppression_minimum_days=1,
        backup_deletion_propagation_max_days=1,
        restoration_requires_suppressions=True,
    )

    with pytest.raises(KeyError, match="no retention rule"):
        policy.retention_deadline(DataCategory.PUBLIC_TENDER, NOW)
    with pytest.raises(KeyError, match="no retention rule"):
        policy.review_deadline(DataCategory.PUBLIC_TENDER, NOW)


@pytest.mark.parametrize(
    ("retention_days", "review_days", "message"),
    [
        (0, 1, "retention_days"),
        (10, 0, "review_interval_days"),
        (10, 11, "cannot exceed"),
    ],
)
def test_retention_rule_validation(
    retention_days: int,
    review_days: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        RetentionRule(retention_days, review_days)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"version": 0}, "version"),
        ({"suppression_minimum_days": 0}, "suppression_minimum_days"),
        ({"backup_deletion_propagation_max_days": 0}, "backup deletion"),
    ],
)
def test_retention_policy_validation(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "version": 1,
        "rules": {},
        "prohibited_categories": frozenset(),
        "suppression_minimum_days": 1,
        "backup_deletion_propagation_max_days": 1,
        "restoration_requires_suppressions": True,
    }
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        RetentionPolicy(**values)  # type: ignore[arg-type]


def test_retention_rejects_naive_timestamp() -> None:
    policy = load_retention_policy(Path("policies/retention.yml"))

    with pytest.raises(ValueError, match="timezone-aware"):
        policy.retention_deadline(
            DataCategory.ORGANIZATION_METADATA,
            datetime(2026, 8, 3),
        )


def test_suppression_is_hashed_and_matches_normalized_email() -> None:
    entry = create_suppression(
        " Person@Example.org ",
        SuppressionChannel.EMAIL,
        SuppressionReason.OBJECTION,
        pepper=PEPPER,
        now=NOW,
        minimum_retention_days=1095,
        source="privacy-request",
    )

    assert entry.subject_hash != "person@example.org"
    assert entry.matches("person@example.org", pepper=PEPPER) is True
    assert entry.matches("other@example.org", pepper=PEPPER) is False
    assert entry.expires_at == NOW + timedelta(days=1095)


def test_phone_normalization_ignores_formatting() -> None:
    digest = hash_identifier(
        "+33 (0)1 23 45 67 89",
        SuppressionChannel.PHONE,
        pepper=PEPPER,
    )

    assert digest == hash_identifier(
        "330123456789",
        SuppressionChannel.PHONE,
        pepper=PEPPER,
    )


@pytest.mark.parametrize(
    ("identifier", "channel", "message"),
    [
        ("", SuppressionChannel.EMAIL, "identifier"),
        ("no-digits", SuppressionChannel.PHONE, "digits"),
    ],
)
def test_identifier_normalization_validation(
    identifier: str,
    channel: SuppressionChannel,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        normalize_identifier(identifier, channel)


def test_hash_requires_pepper() -> None:
    with pytest.raises(ValueError, match="pepper"):
        hash_identifier("person@example.org", SuppressionChannel.EMAIL, pepper=b"")


def test_create_suppression_validates_retention_and_time() -> None:
    with pytest.raises(ValueError, match="minimum_retention_days"):
        create_suppression(
            "person@example.org",
            SuppressionChannel.EMAIL,
            SuppressionReason.OBJECTION,
            pepper=PEPPER,
            now=NOW,
            minimum_retention_days=0,
            source="request",
        )
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        create_suppression(
            "person@example.org",
            SuppressionChannel.EMAIL,
            SuppressionReason.OBJECTION,
            pepper=PEPPER,
            now=datetime(2026, 8, 3),
            minimum_retention_days=1,
            source="request",
        )


def test_suppression_entry_validation() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        SuppressionEntry("bad", SuppressionChannel.EMAIL, SuppressionReason.OBJECTION, NOW, NOW + timedelta(days=1), "request")
    digest = "a" * 64
    with pytest.raises(ValueError, match="source"):
        SuppressionEntry(digest, SuppressionChannel.EMAIL, SuppressionReason.OBJECTION, NOW, NOW + timedelta(days=1), "")
    with pytest.raises(ValueError, match="later"):
        SuppressionEntry(digest, SuppressionChannel.EMAIL, SuppressionReason.OBJECTION, NOW, NOW, "request")

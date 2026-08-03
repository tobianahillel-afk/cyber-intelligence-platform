from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cip.modules.evidence.domain.entities import Evidence
from cip.modules.organizations.domain.entities import Organization

NOW = datetime(2026, 8, 3, 16, 0, tzinfo=UTC)
LATER = NOW + timedelta(days=1)


def test_organization_normalizes_name_and_dates() -> None:
    organization = Organization(
        canonical_name="  Example SA  ",
        legal_name="Example SA",
        country_code="FR",
        website_url="https://example.org",
        created_at=NOW,
        updated_at=LATER,
    )

    assert organization.canonical_name == "Example SA"
    assert organization.created_at.tzinfo is UTC


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"canonical_name": "   "}, "canonical_name is required"),
        ({"canonical_name": "x" * 301}, "cannot exceed"),
        ({"legal_name": "x" * 301}, "legal_name"),
        ({"country_code": "fr"}, "ISO 3166"),
        ({"website_url": "mailto:test@example.org"}, "website_url"),
        ({"created_at": datetime(2026, 8, 3)}, "timezone-aware"),
        ({"updated_at": NOW - timedelta(seconds=1)}, "cannot precede"),
    ],
)
def test_organization_rejects_invalid_values(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "canonical_name": "Example",
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        Organization(**values)  # type: ignore[arg-type]


def test_evidence_accepts_provenance_and_retention() -> None:
    evidence = Evidence(
        source_id="official-source",
        source_url="https://example.org/record/1",
        summary="Official public record",
        confidence=0.95,
        collected_at=NOW,
        published_at=NOW - timedelta(hours=1),
        observed_at=NOW - timedelta(hours=2),
        content_hash_sha256="a" * 64,
        raw_storage_uri="s3://evidence/record-1",
        raw_storage_permitted=True,
        retention_until=LATER,
    )

    assert evidence.content_hash_sha256 == "a" * 64
    assert evidence.retention_until == LATER


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"source_id": ""}, "source_id"),
        ({"source_url": "mailto:test@example.org"}, "source_url"),
        ({"summary": ""}, "summary"),
        ({"summary": "x" * 4_001}, "4000"),
        ({"confidence": -0.1}, "between 0 and 1"),
        ({"confidence": 1.1}, "between 0 and 1"),
        ({"collected_at": datetime(2026, 8, 3)}, "timezone-aware"),
        ({"content_hash_sha256": "ABC"}, "SHA-256"),
        ({"raw_storage_uri": "s3://bucket/key"}, "raw_storage_uri"),
        ({"retention_until": NOW}, "later than collected_at"),
    ],
)
def test_evidence_rejects_invalid_values(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "source_id": "source",
        "source_url": "https://example.org/evidence",
        "summary": "Evidence",
        "confidence": 0.5,
        "collected_at": NOW,
    }
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        Evidence(**values)  # type: ignore[arg-type]

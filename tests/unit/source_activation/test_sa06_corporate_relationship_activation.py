from pathlib import Path

from cip.modules.source_activation.domain.models import ActivationDisposition, ActivationRecord
from cip.modules.source_activation.infrastructure.inventory import load_activation_inventory

ACTIVATION_PATH = Path("policies/source_activation.yml")
DOC_PATH = Path("docs/source_activation/SA_06_CORPORATE_RELATIONSHIP_ACTIVATION.md")

MANUAL = {
    "official-corporate-disclosures",
    "official-regulatory-change-notices",
    "official-relationship-disclosures",
    "public-partner-directory-metadata",
    "public-case-study-metadata",
    "public-certificate-relationship-metadata",
}
LICENSED = "licensed-corporate-news-metadata"


def test_sa06_public_official_families_are_terminal_manual_review_paths() -> None:
    records = _records()
    for source_id in MANUAL:
        record = records[source_id]
        assert record.disposition is ActivationDisposition.MANUAL
        assert record.activation_wave == "SA-06"
        assert record.reason
        assert record.is_resolved
        assert not record.is_executable


def test_sa06_licensed_news_is_owned_fail_closed_by_sa07() -> None:
    record = _records()[LICENSED]
    assert record.disposition is ActivationDisposition.BLOCKED
    assert record.activation_wave == "SA-07"
    assert record.reason
    assert record.is_resolved
    assert not record.is_executable


def test_sa06_decision_record_covers_every_family() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    for source_id in MANUAL | {LICENSED}:
        assert f"`{source_id}`" in text


def _records() -> dict[str, ActivationRecord]:
    return {record.source_id: record for record in load_activation_inventory(ACTIVATION_PATH)}

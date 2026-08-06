from __future__ import annotations

from pathlib import Path

from cip.modules.source_governance.domain.models import DataCategory, SourceStatus
from cip.modules.source_governance.infrastructure.registry import load_source_registry
from cip.modules.source_portfolio.domain.models import CatalogStatus
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio

SOURCE_PATH = Path("policies/sources.threat_telemetry.yml")
PORTFOLIO_PATH = Path("policies/source_portfolio.threat_telemetry.yml")
EXPECTED_IDS = {
    "licensed-stix-taxii",
    "licensed-phishing-metadata",
    "licensed-passive-dns",
    "licensed-certificate-telemetry",
    "licensed-malware-metadata",
}
PROHIBITED = {
    DataCategory.CREDENTIAL,
    DataCategory.VICTIM_FILE,
    DataCategory.PRIVATE_COMMUNICATION,
    DataCategory.PRIVATE_PERSONAL_DATA,
    DataCategory.RESTRICTED_CONTENT,
}


def test_threat_sources_are_governed_but_not_authorized() -> None:
    entries = load_source_registry(SOURCE_PATH)

    assert {entry.policy.id for entry in entries} == EXPECTED_IDS
    assert all(entry.policy.status is SourceStatus.DRAFT for entry in entries)
    assert all(not entry.authorization.automated_collection_allowed for entry in entries)
    assert all(not entry.authorization.approved_hosts for entry in entries)
    assert all(
        entry.policy.prohibited_data_categories >= PROHIBITED
        for entry in entries
    )
    assert all(not entry.policy.raw_content_storage for entry in entries)


def test_threat_portfolio_entries_are_non_executable_candidates() -> None:
    entries = load_source_portfolio(PORTFOLIO_PATH)

    assert {entry.source_id for entry in entries} == EXPECTED_IDS
    assert all(entry.status is CatalogStatus.CANDIDATE for entry in entries)
    assert all(not entry.executable for entry in entries)
    assert all(entry.adapter is not None for entry in entries)
    assert all(
        entry.metadata.get("direct_indicator_connection") == "forbidden"
        for entry in entries
    )
    assert all(
        entry.metadata.get("binary_collection") == "forbidden"
        for entry in entries
    )
    assert all(
        entry.metadata.get("organization_compromise_inference") == "forbidden"
        for entry in entries
    )

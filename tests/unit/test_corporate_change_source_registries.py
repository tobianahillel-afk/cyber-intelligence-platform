from __future__ import annotations

from pathlib import Path

from cip.modules.source_governance.domain.models import DataCategory, SourceStatus
from cip.modules.source_governance.infrastructure.registry import load_source_registry
from cip.modules.source_portfolio.domain.models import CatalogStatus
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio

SOURCE_PATH = Path("policies/sources.corporate_changes.yml")
PORTFOLIO_PATH = Path("policies/source_portfolio.corporate_changes.yml")
EXPECTED_IDS = {
    "official-corporate-disclosures",
    "official-regulatory-change-notices",
    "licensed-corporate-news-metadata",
}
PROHIBITED = {
    DataCategory.CREDENTIAL,
    DataCategory.VICTIM_FILE,
    DataCategory.PRIVATE_COMMUNICATION,
    DataCategory.PRIVATE_PERSONAL_DATA,
    DataCategory.RESTRICTED_CONTENT,
}


def test_corporate_change_sources_are_governed_but_not_authorized() -> None:
    entries = load_source_registry(SOURCE_PATH)

    assert {entry.policy.id for entry in entries} == EXPECTED_IDS
    assert all(entry.policy.status is SourceStatus.DRAFT for entry in entries)
    assert all(not entry.authorization.automated_collection_allowed for entry in entries)
    assert all(not entry.authorization.approved_hosts for entry in entries)
    assert all(not entry.authorization.approved_path_prefixes for entry in entries)
    assert all(entry.policy.prohibited_data_categories >= PROHIBITED for entry in entries)
    assert all(not entry.policy.raw_content_storage for entry in entries)
    assert all(entry.policy.human_review_required for entry in entries)


def test_corporate_change_portfolio_entries_are_non_executable_candidates() -> None:
    entries = load_source_portfolio(PORTFOLIO_PATH)

    assert {entry.source_id for entry in entries} == EXPECTED_IDS
    assert all(entry.status is CatalogStatus.CANDIDATE for entry in entries)
    assert all(not entry.executable for entry in entries)
    assert all(entry.adapter is not None for entry in entries)
    assert all(entry.metadata.get("authorization_status") == "missing" for entry in entries)
    assert all(entry.metadata.get("full_text_storage") == "forbidden" for entry in entries)
    assert all(entry.metadata.get("paywall_bypass") == "forbidden" for entry in entries)
    assert all(
        entry.metadata.get("authentication_bypass") == "forbidden"
        for entry in entries
    )
    assert all(entry.metadata.get("private_source_access") == "forbidden" for entry in entries)
    assert all(entry.metadata.get("automatic_opportunity") == "forbidden" for entry in entries)
    assert all(entry.metadata.get("contact_enrichment") == "forbidden" for entry in entries)
    assert all(entry.metadata.get("autonomous_outreach") == "forbidden" for entry in entries)

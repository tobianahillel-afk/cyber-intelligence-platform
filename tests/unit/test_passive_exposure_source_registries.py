from __future__ import annotations

from pathlib import Path

from cip.modules.source_governance.domain.models import DataCategory, SourceStatus
from cip.modules.source_governance.infrastructure.registry import load_source_registry
from cip.modules.source_portfolio.domain.models import CatalogStatus
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio

SOURCE_PATH = Path("policies/sources.passive_exposure.yml")
PORTFOLIO_PATH = Path("policies/source_portfolio.passive_exposure.yml")
EXPECTED_IDS = {
    "licensed-passive-exposure",
    "licensed-technographic-observations",
    "licensed-cloud-asset-observations",
}
PROHIBITED = {
    DataCategory.CREDENTIAL,
    DataCategory.VICTIM_FILE,
    DataCategory.PRIVATE_COMMUNICATION,
    DataCategory.PRIVATE_PERSONAL_DATA,
    DataCategory.RESTRICTED_CONTENT,
}


def test_passive_sources_are_governed_but_not_authorized() -> None:
    entries = load_source_registry(SOURCE_PATH)

    assert {entry.policy.id for entry in entries} == EXPECTED_IDS
    assert all(entry.policy.status is SourceStatus.DRAFT for entry in entries)
    assert all(not entry.authorization.automated_collection_allowed for entry in entries)
    assert all(not entry.authorization.approved_hosts for entry in entries)
    assert all(not entry.authorization.approved_path_prefixes for entry in entries)
    assert all(
        entry.policy.prohibited_data_categories >= PROHIBITED
        for entry in entries
    )
    assert all(not entry.policy.raw_content_storage for entry in entries)
    assert all(entry.policy.human_review_required for entry in entries)


def test_passive_portfolio_entries_are_non_executable_candidates() -> None:
    entries = load_source_portfolio(PORTFOLIO_PATH)

    assert {entry.source_id for entry in entries} == EXPECTED_IDS
    assert all(entry.status is CatalogStatus.CANDIDATE for entry in entries)
    assert all(not entry.executable for entry in entries)
    assert all(entry.adapter is not None for entry in entries)
    assert all(entry.metadata.get("active_probe") == "forbidden" for entry in entries)
    assert all(
        entry.metadata.get("credential_use") == "forbidden" for entry in entries
    )
    assert all(
        entry.metadata.get("vulnerability_applicability") == "not_assessed"
        for entry in entries
    )
    assert all(
        entry.metadata.get("exposure_verification") == "forbidden"
        for entry in entries
    )
    assert all(
        entry.metadata.get("organization_compromise_inference") == "forbidden"
        for entry in entries
    )

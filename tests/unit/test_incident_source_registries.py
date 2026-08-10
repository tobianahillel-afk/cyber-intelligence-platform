from __future__ import annotations

from pathlib import Path

from cip.modules.source_governance.domain.models import (
    DataCategory,
    SourceStatus,
)
from cip.modules.source_governance.infrastructure.registry import load_source_registry
from cip.modules.source_portfolio.domain.models import CatalogStatus
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio

SOURCE_PATH = Path("policies/sources.incidents.yml")
PORTFOLIO_PATH = Path("policies/source_portfolio.incidents.yml")
SEC_SOURCE_ID = "sec-cyber-disclosures"
CANDIDATE_IDS = {
    "official-company-incident-disclosures",
    "regulator-cert-incident-notices",
    "licensed-incident-reporting",
    "licensed-ransomware-metadata",
}
EXPECTED_IDS = CANDIDATE_IDS | {SEC_SOURCE_ID}
PROHIBITED = {
    DataCategory.CREDENTIAL,
    DataCategory.VICTIM_FILE,
    DataCategory.PRIVATE_COMMUNICATION,
    DataCategory.PRIVATE_PERSONAL_DATA,
    DataCategory.RESTRICTED_CONTENT,
}


def test_incident_sources_preserve_governance_across_activation_states() -> None:
    entries = load_source_registry(SOURCE_PATH)
    by_id = {entry.policy.id: entry for entry in entries}

    assert set(by_id) == EXPECTED_IDS
    sec = by_id[SEC_SOURCE_ID]
    assert sec.policy.status is SourceStatus.ENABLED
    assert sec.authorization.automated_collection_allowed is True
    assert sec.authorization.approved_hosts == frozenset({"data.sec.gov"})

    for source_id in CANDIDATE_IDS:
        entry = by_id[source_id]
        assert entry.policy.status is SourceStatus.DRAFT
        assert entry.authorization.automated_collection_allowed is False
        assert not entry.authorization.approved_hosts

    assert all(
        entry.policy.prohibited_data_categories >= PROHIBITED
        for entry in entries
    )
    assert all(not entry.policy.raw_content_storage for entry in entries)


def test_incident_portfolio_distinguishes_sec_from_candidates() -> None:
    entries = load_source_portfolio(PORTFOLIO_PATH)
    by_id = {entry.source_id: entry for entry in entries}

    assert set(by_id) == EXPECTED_IDS
    sec = by_id[SEC_SOURCE_ID]
    assert sec.status is CatalogStatus.EXECUTABLE
    assert sec.executable is True
    assert sec.adapter is not None

    for source_id in CANDIDATE_IDS:
        entry = by_id[source_id]
        assert entry.status is CatalogStatus.CANDIDATE
        assert entry.executable is False
        assert entry.adapter is not None

    assert all(
        entry.metadata.get("victim_content_collection") == "forbidden"
        for entry in entries
    )
    assert all(
        entry.metadata.get("threat_actor_interaction") == "forbidden"
        for entry in entries
    )
    assert all(
        entry.metadata.get("autonomous_outreach") == "forbidden"
        for entry in entries
    )

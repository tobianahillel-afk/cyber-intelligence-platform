from __future__ import annotations

from pathlib import Path

from cip.modules.source_governance.domain.models import DataCategory, SourceStatus
from cip.modules.source_governance.infrastructure.registry import load_source_registry
from cip.modules.source_portfolio.domain.models import CatalogStatus
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio

SOURCE_PATH = Path("policies/sources.threat_telemetry.yml")
PORTFOLIO_PATH = Path("policies/source_portfolio.threat_telemetry.yml")
PHISHTANK_SOURCE_ID = "phishtank-verified-online"
CANDIDATE_IDS = {
    "licensed-stix-taxii",
    "licensed-phishing-metadata",
    "licensed-passive-dns",
    "licensed-certificate-telemetry",
    "licensed-malware-metadata",
}
EXPECTED_IDS = CANDIDATE_IDS | {PHISHTANK_SOURCE_ID}
PROHIBITED = {
    DataCategory.CREDENTIAL,
    DataCategory.VICTIM_FILE,
    DataCategory.PRIVATE_COMMUNICATION,
    DataCategory.PRIVATE_PERSONAL_DATA,
    DataCategory.RESTRICTED_CONTENT,
}


def test_threat_sources_preserve_governance_across_activation_states() -> None:
    entries = load_source_registry(SOURCE_PATH)
    by_id = {entry.policy.id: entry for entry in entries}

    assert set(by_id) == EXPECTED_IDS
    phishtank = by_id[PHISHTANK_SOURCE_ID]
    assert phishtank.policy.status is SourceStatus.ENABLED
    assert phishtank.authorization.automated_collection_allowed is True
    assert phishtank.authorization.approved_hosts == frozenset({"data.phishtank.com"})

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


def test_threat_portfolio_distinguishes_phishtank_from_candidates() -> None:
    entries = load_source_portfolio(PORTFOLIO_PATH)
    by_id = {entry.source_id: entry for entry in entries}

    assert set(by_id) == EXPECTED_IDS
    phishtank = by_id[PHISHTANK_SOURCE_ID]
    assert phishtank.status is CatalogStatus.EXECUTABLE
    assert phishtank.executable is True
    assert phishtank.adapter is not None

    for source_id in CANDIDATE_IDS:
        entry = by_id[source_id]
        assert entry.status is CatalogStatus.CANDIDATE
        assert entry.executable is False
        assert entry.adapter is not None

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

from __future__ import annotations

from pathlib import Path

from cip.modules.source_governance.domain.models import AuthorizationStatus, SourceStatus
from cip.modules.source_governance.infrastructure.registry import load_source_registry
from cip.modules.source_portfolio.domain.models import CatalogStatus
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio

SOURCE_REGISTRY = Path("policies/sources.relationships.yml")
SOURCE_PORTFOLIO = Path("policies/source_portfolio.relationships.yml")


def test_relationship_source_registry_is_not_authorized_for_execution() -> None:
    entries = load_source_registry(SOURCE_REGISTRY)

    assert len(entries) == 4
    for entry in entries:
        assert entry.policy.status is SourceStatus.DRAFT
        assert entry.authorization.status is AuthorizationStatus.MISSING
        assert entry.authorization.approved_hosts == frozenset()
        assert entry.authorization.approved_path_prefixes == ()
        assert entry.authorization.automated_collection_allowed is False
        assert entry.policy.raw_content_storage is False


def test_relationship_source_portfolio_candidates_are_non_executable() -> None:
    entries = load_source_portfolio(SOURCE_PORTFOLIO)

    assert len(entries) == 4
    for entry in entries:
        assert entry.status is CatalogStatus.CANDIDATE
        assert entry.executable is False
        assert entry.candidate_origin == "lot-19"
        assert entry.metadata["executable"] is False
        assert entry.metadata["authorization_status"] == "missing"
        assert entry.metadata["private_portal_access"] == "forbidden"
        assert entry.metadata["personal_network_access"] == "forbidden"
        assert entry.metadata["automatic_opportunity"] == "forbidden"
        assert entry.metadata["contact_enrichment"] == "forbidden"
        assert entry.metadata["autonomous_outreach"] == "forbidden"

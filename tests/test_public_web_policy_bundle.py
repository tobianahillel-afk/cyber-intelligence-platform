from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from cip.adapters.sources.public_web.registry import load_public_web_targets
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    SourceStatus,
)
from cip.modules.source_governance.infrastructure.registry import load_source_registry
from cip.modules.source_portfolio.domain.models import CatalogStatus
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio

NOW = datetime(2026, 8, 6, 10, 0, tzinfo=UTC)
SOURCE_ID = "public-web-example-fr-organization"


def test_public_web_example_is_consistent_and_non_executable() -> None:
    targets = load_public_web_targets(Path("policies/public_web_targets.yml"))
    sources = load_source_registry(Path("policies/sources.public_web.yml"))
    portfolio = load_source_portfolio(Path("policies/source_portfolio.public_web.yml"))

    assert len(targets) == len(sources) == len(portfolio) == 1
    target = targets[0]
    source = sources[0]
    catalog = portfolio[0]
    assert target.id == source.policy.id == catalog.source_id == SOURCE_ID
    assert not target.enabled
    assert not target.executable_at(NOW)
    assert source.policy.status is SourceStatus.DRAFT
    assert source.authorization.status is AuthorizationStatus.MISSING
    assert not source.authorization.automated_collection_allowed
    assert source.authorization.approved_hosts == frozenset()
    assert catalog.status is CatalogStatus.CANDIDATE
    assert catalog.adapter is not None
    assert catalog.adapter.supports_tombstones

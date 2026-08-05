from __future__ import annotations

from pathlib import Path

import pytest

from cip.modules.source_portfolio.domain.models import CatalogStatus, CollectionMode
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio


def test_load_source_portfolio_catalog() -> None:
    entries = load_source_portfolio(Path("policies/source_portfolio.yml"))
    entries_by_id = {entry.source_id: entry for entry in entries}

    assert entries_by_id["cisa-kev"].status is CatalogStatus.EXECUTABLE
    assert entries_by_id["cisa-kev"].adapter is not None
    assert entries_by_id["cisa-kev"].adapter.supports(
        CollectionMode.CONDITIONAL_REFRESH
    )
    assert entries_by_id["reference-synthetic"].adapter is not None
    assert entries_by_id["osint-framework-import"].executable is False
    assert entries_by_id["brixhub"].metadata["quarantine"] is True


def test_registry_rejects_duplicate_source_ids(tmp_path: Path) -> None:
    path = tmp_path / "portfolio.yml"
    path.write_text(
        """version: 1
sources:
  - source_id: duplicate
    display_name: Duplicate
    canonical_url: https://example.test/one
    category: candidate
    status: candidate
    freshness_max_age_seconds: 300
    commercial_use_cases: [source_discovery]
    candidate_origin: test
  - source_id: duplicate
    display_name: Duplicate again
    canonical_url: https://example.test/two
    category: candidate
    status: candidate
    freshness_max_age_seconds: 300
    commercial_use_cases: [source_discovery]
    candidate_origin: test
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate"):
        load_source_portfolio(path)


def test_registry_rejects_executable_without_manifest(tmp_path: Path) -> None:
    path = tmp_path / "portfolio.yml"
    path.write_text(
        """version: 1
sources:
  - source_id: invalid
    display_name: Invalid
    canonical_url: https://example.test/invalid
    category: invalid
    status: executable
    freshness_max_age_seconds: 300
    commercial_use_cases: [invalid]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="adapter"):
        load_source_portfolio(path)

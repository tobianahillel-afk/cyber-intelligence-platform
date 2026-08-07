from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine

from cip.modules.collection_orchestration.application.runtime import (
    build_collection_runtime,
)
from cip.shared.config.settings import Settings
from cip.shared.persistence.metadata import get_metadata

EXPECTED_IDS = {
    "official-vendor-psirt",
    "official-linux-security-advisories",
    "official-package-security-advisories",
}


def test_advisory_policy_paths_have_safe_defaults() -> None:
    settings = Settings(environment="development", _env_file=None)

    assert settings.advisory_source_registry_path == Path(
        "policies/sources.advisories.yml"
    )
    assert settings.advisory_source_portfolio_path == Path(
        "policies/source_portfolio.advisories.yml"
    )


def test_runtime_syncs_advisory_candidates_without_execution(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'runtime.sqlite'}"
    engine = create_engine(database_url)
    get_metadata().create_all(engine)
    runtime = build_collection_runtime(
        Settings(
            environment="test",
            database_url=database_url,
            control_plane_token="test-control-token-123",
            _env_file=None,
        )
    )

    portfolio_by_id = {entry.source_id: entry for entry in runtime.portfolio}
    adapter_sources = {source_id for source_id, _ in runtime.adapters}
    assert set(portfolio_by_id) >= EXPECTED_IDS
    assert all(not portfolio_by_id[source_id].executable for source_id in EXPECTED_IDS)
    assert adapter_sources.isdisjoint(EXPECTED_IDS)
    assert all(schedule.source_id not in EXPECTED_IDS for schedule in runtime.schedules)

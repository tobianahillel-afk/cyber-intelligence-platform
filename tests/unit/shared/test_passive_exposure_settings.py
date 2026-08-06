from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine

from cip.modules.collection_orchestration.application.runtime import (
    build_collection_runtime,
)
from cip.shared.config.settings import Settings
from cip.shared.persistence.metadata import get_metadata

EXPECTED_IDS = {
    "licensed-passive-exposure",
    "licensed-technographic-observations",
    "licensed-cloud-asset-observations",
}


def test_passive_exposure_policy_paths_have_safe_defaults() -> None:
    settings = Settings(environment="development", _env_file=None)

    assert settings.passive_exposure_source_registry_path == Path(
        "policies/sources.passive_exposure.yml"
    )
    assert settings.passive_exposure_source_portfolio_path == Path(
        "policies/source_portfolio.passive_exposure.yml"
    )


def test_runtime_syncs_candidates_without_adapters_or_schedules(tmp_path: Path) -> None:
    database_path = tmp_path / "runtime.sqlite"
    database_url = f"sqlite+pysqlite:///{database_path}"
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
    assert set(portfolio_by_id) >= EXPECTED_IDS
    assert all(not portfolio_by_id[source_id].executable for source_id in EXPECTED_IDS)
    assert all(
        source_id not in {adapter_source for adapter_source, _ in runtime.adapters}
        for source_id in EXPECTED_IDS
    )
    assert all(schedule.source_id not in EXPECTED_IDS for schedule in runtime.schedules)

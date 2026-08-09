from __future__ import annotations

from pathlib import Path

from cip.modules.collection_orchestration.application.runtime import build_collection_runtime
from cip.shared.config.settings import Settings
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine


def test_runtime_registers_sa04_adapters_with_deployment_schedules_disabled(
    tmp_path: Path,
) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'sa04-runtime.db'}",
    )
    get_metadata().create_all(create_database_engine(settings.database_url))

    runtime = build_collection_runtime(settings)

    assert ("sec-cyber-disclosures", "sec-submissions-item-1-05") in runtime.adapters
    assert ("phishtank-verified-online", "phishtank-online-valid-json") in runtime.adapters
    schedules = {
        (schedule.source_id, schedule.adapter_id): schedule
        for schedule in runtime.schedules
        if schedule.source_id in {"sec-cyber-disclosures", "phishtank-verified-online"}
    }
    assert set(schedules) == {
        ("sec-cyber-disclosures", "sec-submissions-item-1-05"),
        ("phishtank-verified-online", "phishtank-online-valid-json"),
    }
    assert all(not schedule.enabled for schedule in schedules.values())

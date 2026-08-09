from __future__ import annotations

from pathlib import Path

from cip.modules.collection_orchestration.application.runtime import build_collection_runtime
from cip.shared.config.settings import Settings
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine


def test_runtime_registers_passive_adapters_without_enabling_schedules(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'passive-runtime.db'}",
    )
    get_metadata().create_all(create_database_engine(settings.database_url))

    runtime = build_collection_runtime(settings)

    assert ("cloudflare-doh", "cloudflare-dns-json") in runtime.adapters
    assert ("certspotter-ct", "certspotter-issuances-api") in runtime.adapters
    passive_schedules = {
        (schedule.source_id, schedule.adapter_id): schedule
        for schedule in runtime.schedules
        if schedule.source_id in {"cloudflare-doh", "certspotter-ct"}
    }
    assert set(passive_schedules) == {
        ("cloudflare-doh", "cloudflare-dns-json"),
        ("certspotter-ct", "certspotter-issuances-api"),
    }
    assert all(not schedule.enabled for schedule in passive_schedules.values())

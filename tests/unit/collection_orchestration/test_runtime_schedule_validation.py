from __future__ import annotations

import pytest

from cip.modules.collection_orchestration.application.runtime import (
    _validate_registered_schedules,
)
from cip.modules.collection_orchestration.domain.models import SourceSchedule
from cip.modules.source_portfolio.domain.models import (
    AdapterCapabilityManifest,
    CatalogStatus,
    CollectionMode,
    SourceCatalogEntry,
)


def test_conditional_paused_schedule_allows_missing_runtime_adapter() -> None:
    schedule = SourceSchedule(
        source_id="conditional",
        adapter_id="conditional-adapter",
        interval_seconds=300,
    )
    entry = SourceCatalogEntry(
        source_id="conditional",
        display_name="Conditional",
        canonical_url="https://example.test/conditional",
        category="test",
        status=CatalogStatus.PAUSED,
        freshness_max_age_seconds=300,
        commercial_use_cases=("test",),
        adapter=_manifest("conditional", "conditional-adapter"),
        metadata={"activation_requires": "target"},
    )

    _validate_registered_schedules((schedule,), {}, (entry,))


def test_static_schedule_requires_registered_runtime_adapter() -> None:
    schedule = SourceSchedule(
        source_id="static",
        adapter_id="static-adapter",
        interval_seconds=300,
    )
    entry = SourceCatalogEntry(
        source_id="static",
        display_name="Static",
        canonical_url="https://example.test/static",
        category="test",
        status=CatalogStatus.EXECUTABLE,
        freshness_max_age_seconds=300,
        commercial_use_cases=("test",),
        adapter=_manifest("static", "static-adapter"),
    )

    with pytest.raises(ValueError, match="static/static-adapter"):
        _validate_registered_schedules((schedule,), {}, (entry,))


def test_plain_paused_schedule_does_not_hide_missing_adapter() -> None:
    schedule = SourceSchedule(
        source_id="paused-static",
        adapter_id="static-adapter",
        interval_seconds=300,
    )
    entry = SourceCatalogEntry(
        source_id="paused-static",
        display_name="Paused static",
        canonical_url="https://example.test/paused-static",
        category="test",
        status=CatalogStatus.PAUSED,
        freshness_max_age_seconds=300,
        commercial_use_cases=("test",),
        adapter=_manifest("paused-static", "static-adapter"),
    )

    with pytest.raises(ValueError, match="paused-static/static-adapter"):
        _validate_registered_schedules((schedule,), {}, (entry,))


def _manifest(source_id: str, adapter_id: str) -> AdapterCapabilityManifest:
    return AdapterCapabilityManifest(
        source_id=source_id,
        adapter_id=adapter_id,
        adapter_version="1",
        provider_schema_version="v1",
        modes=frozenset({CollectionMode.INCREMENTAL_CURSOR}),
        canonical_output_types=("raw_observation",),
    )

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cip.modules.source_portfolio.domain.models import (
    AdapterCapabilityManifest,
    BackfillState,
    CatalogStatus,
    CollectionMode,
    SourceCatalogEntry,
)


def manifest() -> AdapterCapabilityManifest:
    return AdapterCapabilityManifest(
        source_id="reference",
        adapter_id="reference-adapter",
        adapter_version="1",
        provider_schema_version="v1",
        modes=frozenset(
            {CollectionMode.HISTORICAL_BACKFILL, CollectionMode.INCREMENTAL_CURSOR}
        ),
        canonical_output_types=("source_record",),
        supports_corrections=True,
        max_page_size=50,
        max_window_days=7,
    )


def test_executable_entry_requires_matching_adapter() -> None:
    entry = SourceCatalogEntry(
        source_id="reference",
        display_name="Reference",
        canonical_url="https://example.test/reference",
        category="test",
        status=CatalogStatus.EXECUTABLE,
        freshness_max_age_seconds=300,
        commercial_use_cases=("runtime_validation",),
        adapter=manifest(),
    )

    assert entry.executable is True
    assert entry.adapter is not None
    assert entry.adapter.supports(CollectionMode.HISTORICAL_BACKFILL)


def test_candidate_requires_origin_and_is_not_executable() -> None:
    with pytest.raises(ValueError, match="candidate_origin"):
        SourceCatalogEntry(
            source_id="candidate",
            display_name="Candidate",
            canonical_url="https://example.test/candidate",
            category="candidate",
            status=CatalogStatus.CANDIDATE,
            freshness_max_age_seconds=300,
            commercial_use_cases=("source_discovery",),
        )


def test_catalog_rejects_insecure_url_and_naive_dates() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        SourceCatalogEntry(
            source_id="candidate",
            display_name="Candidate",
            canonical_url="http://example.test/candidate",
            category="candidate",
            status=CatalogStatus.CANDIDATE,
            freshness_max_age_seconds=300,
            commercial_use_cases=("source_discovery",),
            candidate_origin="test",
        )

    with pytest.raises(ValueError, match="timezone-aware"):
        SourceCatalogEntry(
            source_id="reference",
            display_name="Reference",
            canonical_url="https://example.test/reference",
            category="test",
            status=CatalogStatus.EXECUTABLE,
            freshness_max_age_seconds=300,
            commercial_use_cases=("runtime_validation",),
            adapter=manifest(),
            review_due_at=datetime(2026, 8, 5),
        )


def test_manifest_validates_limits() -> None:
    with pytest.raises(ValueError, match="max_page_size"):
        AdapterCapabilityManifest(
            source_id="reference",
            adapter_id="reference-adapter",
            adapter_version="1",
            provider_schema_version="v1",
            modes=frozenset({CollectionMode.INCREMENTAL_CURSOR}),
            canonical_output_types=("source_record",),
            max_page_size=0,
        )

    entry = SourceCatalogEntry(
        source_id="reference",
        display_name="Reference",
        canonical_url="https://example.test/reference",
        category="test",
        status=CatalogStatus.EXECUTABLE,
        freshness_max_age_seconds=300,
        commercial_use_cases=("runtime_validation",),
        adapter=manifest(),
        authorization_expires_at=datetime(2026, 8, 6, tzinfo=UTC),
    )
    assert entry.authorization_expires_at == datetime(2026, 8, 6, tzinfo=UTC)


def test_failed_backfill_is_retryable_not_terminal() -> None:
    assert BackfillState.FAILED.is_terminal is False
    assert BackfillState.COMPLETED.is_terminal is True
    assert BackfillState.CANCELLED.is_terminal is True

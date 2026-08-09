from __future__ import annotations

from pathlib import Path

from cip.modules.collection_orchestration.infrastructure.schedule_loader import (
    load_collection_schedules,
)
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    SourceStatus,
)
from cip.modules.source_governance.infrastructure.registry import load_source_registry
from cip.modules.source_portfolio.domain.models import CatalogStatus
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio

SOURCE_PATH = Path("policies/sources.passive_infrastructure.yml")
PORTFOLIO_PATH = Path("policies/source_portfolio.passive_infrastructure.yml")
SCHEDULE_PATH = Path("policies/collection_schedules.passive_infrastructure.yml")
EXPECTED_IDS = {"cloudflare-doh", "certspotter-ct"}


def test_passive_sources_are_governed_without_active_validation_authority() -> None:
    entries = load_source_registry(SOURCE_PATH)

    assert {entry.policy.id for entry in entries} == EXPECTED_IDS
    assert all(entry.policy.status is SourceStatus.ENABLED for entry in entries)
    assert all(entry.authorization.status is AuthorizationStatus.APPROVED for entry in entries)
    assert all(entry.authorization.automated_collection_allowed for entry in entries)
    assert all(entry.authorization.approved_hosts for entry in entries)
    assert all(entry.authorization.approved_path_prefixes for entry in entries)
    assert all(
        entry.authorization.approved_purposes == {"passive-infrastructure-intelligence"}
        for entry in entries
    )
    assert all(not entry.policy.raw_content_storage for entry in entries)
    assert all(not entry.authorization.raw_storage_allowed for entry in entries)


def test_passive_portfolio_is_executable_but_never_claims_exposure_or_opportunity() -> None:
    entries = load_source_portfolio(PORTFOLIO_PATH)

    assert {entry.source_id for entry in entries} == EXPECTED_IDS
    assert all(entry.status is CatalogStatus.EXECUTABLE for entry in entries)
    assert all(entry.executable for entry in entries)
    assert all(entry.adapter is not None for entry in entries)
    assert all(entry.metadata.get("active_probe") == "forbidden" for entry in entries)
    assert all(
        entry.metadata.get("direct_asset_connection") == "forbidden" for entry in entries
    )
    assert all(
        entry.metadata.get("vulnerability_applicability") == "not_assessed"
        for entry in entries
    )
    assert all(
        entry.metadata.get("exposure_verification") == "forbidden" for entry in entries
    )
    assert all(entry.metadata.get("automatic_opportunity") == "forbidden" for entry in entries)


def test_passive_schedules_are_checked_in_but_disabled_until_deployment_activation() -> None:
    schedules = load_collection_schedules(SCHEDULE_PATH)

    assert {(item.source_id, item.adapter_id) for item in schedules} == {
        ("cloudflare-doh", "cloudflare-dns-json"),
        ("certspotter-ct", "certspotter-issuances-api"),
    }
    assert all(schedule.enabled is False for schedule in schedules)

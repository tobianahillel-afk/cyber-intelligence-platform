from __future__ import annotations

from pathlib import Path

from cip.modules.collection_orchestration.infrastructure.schedule_bundle import (
    load_collection_schedule_bundle,
)
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    SourceStatus,
)
from cip.modules.source_governance.infrastructure.registry_bundle import (
    load_source_registry_bundle,
)
from cip.modules.source_portfolio.domain.models import CatalogStatus
from cip.modules.source_portfolio.infrastructure.registry_bundle import (
    load_source_portfolio_bundle,
)
from cip.shared.config.settings import Settings

LOT22_SOURCE_IDS = {
    "linkedin-official-api",
    "discord-authorized-integration",
    "brixhub",
    "premium-cti-licensed",
    "commercial-data-licensed",
}


def test_conditional_source_governance_is_fail_closed_by_default() -> None:
    entries = load_source_registry_bundle(
        Path("policies/sources.example.yml"),
        Path("policies/sources.conditional_integrations.yml"),
    )
    by_id = {entry.policy.id: entry for entry in entries}

    assert set(by_id) >= LOT22_SOURCE_IDS
    assert by_id["linkedin-official-api"].policy.status is SourceStatus.PENDING_REVIEW
    assert by_id["brixhub"].policy.status is SourceStatus.QUARANTINED
    for source_id in LOT22_SOURCE_IDS - {"linkedin-official-api", "brixhub"}:
        assert by_id[source_id].policy.status is SourceStatus.DRAFT

    for source_id in LOT22_SOURCE_IDS:
        entry = by_id[source_id]
        assert entry.authorization.status is AuthorizationStatus.MISSING
        assert entry.authorization.document_reference is None
        assert entry.authorization.approved_hosts == frozenset()
        assert entry.authorization.approved_path_prefixes == ()
        assert entry.authorization.approved_purposes == frozenset()
        assert entry.authorization.automated_collection_allowed is False
        assert entry.authorization.raw_storage_allowed is False
        assert entry.policy.raw_content_storage is False
        assert entry.policy.human_review_required is True
        assert DataCategory.CREDENTIAL not in entry.policy.allowed_data_categories
        assert DataCategory.PRIVATE_COMMUNICATION not in entry.policy.allowed_data_categories
        assert DataCategory.PRIVATE_PERSONAL_DATA not in entry.policy.allowed_data_categories
        assert DataCategory.RESTRICTED_CONTENT not in entry.policy.allowed_data_categories


def test_conditional_portfolio_candidates_have_no_adapter_capability() -> None:
    entries = load_source_portfolio_bundle(
        Path("policies/source_portfolio.yml"),
        Path("policies/source_portfolio.conditional_integrations.yml"),
    )
    by_id = {entry.source_id: entry for entry in entries}

    assert set(by_id) >= LOT22_SOURCE_IDS
    for source_id in LOT22_SOURCE_IDS:
        entry = by_id[source_id]
        assert entry.status is CatalogStatus.CANDIDATE
        assert entry.adapter is None
        assert entry.executable is False

    for source_id in LOT22_SOURCE_IDS - {"brixhub"}:
        metadata = by_id[source_id].metadata
        assert metadata["executable"] is False
        assert metadata["runtime_adapter_present"] is False
        assert metadata["schedule_enabled"] is False

    assert by_id["brixhub"].metadata["quarantine"] is True


def test_conditional_candidates_have_no_collection_schedule() -> None:
    settings = Settings(environment="test", _env_file=None)
    schedules = load_collection_schedule_bundle(
        settings.collection_schedule_path,
        settings.decp_collection_schedule_path,
        settings.public_web_collection_schedule_path,
    )

    scheduled_ids = {schedule.source_id for schedule in schedules if schedule.enabled}
    assert LOT22_SOURCE_IDS.isdisjoint(scheduled_ids)


def test_conditional_registry_settings_have_safe_defaults() -> None:
    settings = Settings(environment="test", _env_file=None)

    assert settings.conditional_integration_source_registry_path == Path(
        "policies/sources.conditional_integrations.yml"
    )
    assert settings.conditional_integration_source_portfolio_path == Path(
        "policies/source_portfolio.conditional_integrations.yml"
    )

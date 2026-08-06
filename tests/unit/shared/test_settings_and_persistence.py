from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from cip.shared.config.settings import Settings, get_settings
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import (
    create_database_engine,
    create_session_factory,
    session_scope,
)


def test_settings_have_safe_local_defaults() -> None:
    settings = Settings(environment="development", _env_file=None)

    assert settings.environment == "development"
    assert settings.api_host == "127.0.0.1"
    assert settings.source_registry_path == Path("policies/sources.example.yml")
    assert settings.identity_source_registry_path == Path("policies/identity_sources.yml")
    assert settings.provider_onboarding_registry_path == Path(
        "policies/provider_onboarding.yml"
    )
    assert settings.vulnerability_source_registry_path == Path(
        "policies/sources.vulnerability.yml"
    )
    assert settings.vulnerability_source_portfolio_path == Path(
        "policies/source_portfolio.vulnerability.yml"
    )
    assert settings.incident_source_registry_path == Path(
        "policies/sources.incidents.yml"
    )
    assert settings.incident_source_portfolio_path == Path(
        "policies/source_portfolio.incidents.yml"
    )
    assert settings.greenhouse_board_registry_path == Path(
        "policies/greenhouse_boards.yml"
    )
    assert settings.lever_site_registry_path == Path("policies/lever_sites.yml")
    assert settings.smartrecruiters_company_registry_path == Path(
        "policies/smartrecruiters_companies.yml"
    )
    assert settings.organization_identity_target_registry_path == Path(
        "policies/organization_identity_targets.yml"
    )
    assert settings.collection_schedule_path == Path(
        "policies/collection_schedules.yml"
    )
    assert settings.scheduler_poll_seconds == 5.0
    assert settings.worker_poll_seconds == 2.0


def test_settings_read_prefixed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CIP_ENVIRONMENT", "test")
    monkeypatch.setenv("CIP_API_PORT", "9000")
    monkeypatch.setenv("CIP_LEVER_SITE_REGISTRY_PATH", "custom/lever.yml")

    settings = Settings(_env_file=None)

    assert settings.environment == "test"
    assert settings.api_port == 9000
    assert settings.lever_site_registry_path == Path("custom/lever.yml")


def test_cached_settings_can_be_loaded() -> None:
    get_settings.cache_clear()

    assert get_settings() is get_settings()


def test_database_metadata_contains_foundation_tables() -> None:
    metadata = get_metadata()

    assert set(metadata.tables) == {
        "adapter_capabilities",
        "backfill_partitions",
        "collection_checkpoints",
        "collection_circuits",
        "collection_dead_letters",
        "collection_jobs",
        "commercial_signals",
        "evidence",
        "incident_claim_snapshots",
        "incidents",
        "need_hypotheses",
        "need_hypothesis_signals",
        "opportunities",
        "opportunity_evidence",
        "opportunity_reviews",
        "opportunity_score_components",
        "organization_aliases",
        "organization_identifiers",
        "organization_identities",
        "organization_identity_claims",
        "organization_identity_evidence",
        "organization_merge_candidates",
        "organization_relationships",
        "organizations",
        "procurement_contract_parties",
        "procurement_contracts",
        "procurement_procedures",
        "procurement_publications",
        "procurement_service_classifications",
        "provider_onboarding",
        "provider_onboarding_audit",
        "public_claims",
        "public_resource_versions",
        "public_resources",
        "raw_observations",
        "source_health",
        "source_portfolio",
        "source_portfolio_audit",
        "source_quality_baselines",
        "source_value_events",
        "sources",
        "suppressions",
        "vulnerabilities",
        "vulnerability_affected_ranges",
        "vulnerability_aliases",
        "vulnerability_cwes",
        "vulnerability_exploitation",
        "vulnerability_references",
        "vulnerability_scores",
        "vulnerability_source_snapshots",
    }


def test_metadata_creates_on_sqlite() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")

    get_metadata().create_all(engine)

    assert get_metadata().tables["raw_observations"].foreign_keys
    assert get_metadata().tables["collection_jobs"].foreign_keys
    assert get_metadata().tables["opportunities"].foreign_keys
    assert get_metadata().tables["commercial_signals"].foreign_keys
    assert get_metadata().tables["organization_identities"].foreign_keys
    assert get_metadata().tables["organization_identity_claims"].foreign_keys
    assert get_metadata().tables["provider_onboarding"].foreign_keys
    assert get_metadata().tables["provider_onboarding_audit"].foreign_keys
    assert get_metadata().tables["source_health"].foreign_keys
    assert get_metadata().tables["backfill_partitions"].foreign_keys
    assert get_metadata().tables["source_value_events"].foreign_keys
    assert get_metadata().tables["procurement_publications"].foreign_keys
    assert get_metadata().tables["procurement_contracts"].foreign_keys
    assert get_metadata().tables["procurement_contract_parties"].foreign_keys
    assert get_metadata().tables["public_resources"].foreign_keys
    assert get_metadata().tables["public_resource_versions"].foreign_keys
    assert get_metadata().tables["public_claims"].foreign_keys
    assert get_metadata().tables["vulnerability_aliases"].foreign_keys
    assert get_metadata().tables["vulnerability_source_snapshots"].foreign_keys
    assert get_metadata().tables["vulnerability_scores"].foreign_keys
    assert get_metadata().tables["incidents"].foreign_keys
    assert get_metadata().tables["incident_claim_snapshots"].foreign_keys


def test_database_url_is_required() -> None:
    with pytest.raises(ValueError, match="database_url"):
        create_database_engine("  ")


def test_session_scope_commits_and_rolls_back() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE tx_test (value INTEGER NOT NULL)"))
    factory = create_session_factory(engine)

    with session_scope(factory) as session:
        session.execute(text("INSERT INTO tx_test (value) VALUES (1)"))

    with (
        pytest.raises(RuntimeError, match="rollback"),
        session_scope(factory) as session,
    ):
        session.execute(text("INSERT INTO tx_test (value) VALUES (2)"))
        raise RuntimeError("rollback")

    with engine.connect() as connection:
        count = connection.scalar(text("SELECT COUNT(*) FROM tx_test"))

    assert count == 1

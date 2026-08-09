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
    assert settings.threat_telemetry_source_registry_path == Path(
        "policies/sources.threat_telemetry.yml"
    )
    assert settings.threat_telemetry_source_portfolio_path == Path(
        "policies/source_portfolio.threat_telemetry.yml"
    )
    assert settings.corporate_change_source_registry_path == Path(
        "policies/sources.corporate_changes.yml"
    )
    assert settings.corporate_change_source_portfolio_path == Path(
        "policies/source_portfolio.corporate_changes.yml"
    )
    assert settings.relationship_source_registry_path == Path(
        "policies/sources.relationships.yml"
    )
    assert settings.relationship_source_portfolio_path == Path(
        "policies/source_portfolio.relationships.yml"
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
        "applicability_assessment_snapshots",
        "backfill_partitions",
        "business_relationships",
        "collection_checkpoints",
        "collection_circuits",
        "collection_dead_letters",
        "collection_jobs",
        "commercial_signals",
        "conditional_execution_decisions",
        "conditional_provider_approval_revisions",
        "conditional_provider_approvals",
        "conditional_provider_control_decisions",
        "conditional_provider_runtime_controls",
        "corporate_change_claim_snapshots",
        "corporate_change_events",
        "corporate_change_service_mappings",
        "corporate_graph_edge_snapshots",
        "corporate_graph_edges",
        "corporate_graph_node_snapshots",
        "corporate_graph_nodes",
        "entity_resolution_bindings",
        "entity_resolution_candidates",
        "entity_resolution_decisions",
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
        "passive_assets",
        "passive_observation_snapshots",
        "passive_technologies",
        "procurement_contract_parties",
        "procurement_contracts",
        "procurement_procedures",
        "procurement_publications",
        "procurement_service_classifications",
        "professional_community_contexts",
        "professional_community_snapshots",
        "professional_contact_snapshots",
        "professional_contacts",
        "professional_deletion_audit",
        "professional_people",
        "professional_person_snapshots",
        "professional_reporting_lines",
        "professional_reporting_snapshots",
        "professional_role_snapshots",
        "professional_roles",
        "professional_service_relevance",
        "provider_onboarding",
        "provider_onboarding_audit",
        "public_claims",
        "public_resource_versions",
        "public_resources",
        "raw_observations",
        "relationship_contexts",
        "relationship_evidence_snapshots",
        "source_health",
        "source_portfolio",
        "source_portfolio_audit",
        "source_quality_baselines",
        "source_value_events",
        "sources",
        "suppressions",
        "threat_indicator_relations",
        "threat_indicator_snapshots",
        "threat_indicators",
        "vendor_advisory_ranges",
        "vendor_advisory_revisions",
        "vendor_products",
        "vulnerabilities",
        "vulnerability_affected_ranges",
        "vulnerability_aliases",
        "vulnerability_applicability_assessments",
        "vulnerability_cwes",
        "vulnerability_exploitation",
        "vulnerability_references",
        "vulnerability_scores",
        "vulnerability_source_snapshots",
    }


def test_metadata_creates_on_sqlite() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")

    get_metadata().create_all(engine)

    foreign_key_tables = (
        "raw_observations",
        "collection_jobs",
        "opportunities",
        "commercial_signals",
        "conditional_provider_approval_revisions",
        "conditional_provider_runtime_controls",
        "conditional_provider_control_decisions",
        "conditional_execution_decisions",
        "organization_identities",
        "organization_identity_claims",
        "provider_onboarding",
        "provider_onboarding_audit",
        "source_health",
        "backfill_partitions",
        "source_value_events",
        "procurement_publications",
        "procurement_contracts",
        "procurement_contract_parties",
        "public_resources",
        "public_resource_versions",
        "public_claims",
        "vulnerability_aliases",
        "vulnerability_source_snapshots",
        "vulnerability_scores",
        "incidents",
        "incident_claim_snapshots",
        "threat_indicator_snapshots",
        "threat_indicator_relations",
        "passive_assets",
        "passive_observation_snapshots",
        "passive_technologies",
        "vendor_advisory_ranges",
        "applicability_assessment_snapshots",
        "vulnerability_applicability_assessments",
        "corporate_change_events",
        "corporate_change_claim_snapshots",
        "corporate_change_service_mappings",
        "business_relationships",
        "relationship_evidence_snapshots",
        "relationship_contexts",
        "corporate_graph_nodes",
        "corporate_graph_node_snapshots",
        "corporate_graph_edges",
        "corporate_graph_edge_snapshots",
        "entity_resolution_candidates",
        "entity_resolution_decisions",
        "entity_resolution_bindings",
        "professional_person_snapshots",
        "professional_roles",
        "professional_role_snapshots",
        "professional_reporting_lines",
        "professional_reporting_snapshots",
        "professional_contacts",
        "professional_contact_snapshots",
        "professional_community_contexts",
        "professional_community_snapshots",
        "professional_service_relevance",
        "professional_deletion_audit",
    )
    for table_name in foreign_key_tables:
        assert get_metadata().tables[table_name].foreign_keys


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

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CIP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: str = Field(
        default="postgresql+psycopg://cip:cip@localhost:5432/cip",
        min_length=1,
    )
    source_registry_path: Path = Path("policies/sources.example.yml")
    identity_source_registry_path: Path = Path("policies/identity_sources.yml")
    company_identity_expansion_source_registry_path: Path = Path(
        "policies/sources.company_identity_expansion.yml"
    )
    decp_source_registry_path: Path = Path("policies/sources.decp.yml")
    procurement_funding_source_registry_path: Path = Path(
        "policies/sources.procurement_funding.yml"
    )
    public_web_source_registry_path: Path = Path("policies/sources.public_web.yml")
    vulnerability_source_registry_path: Path = Path("policies/sources.vulnerability.yml")
    search_archive_source_registry_path: Path = Path(
        "policies/sources.search_archives.yml"
    )
    search_provider_source_registry_path: Path = Path(
        "policies/sources.search_providers_sa15.yml"
    )
    incident_source_registry_path: Path = Path("policies/sources.incidents.yml")
    threat_telemetry_source_registry_path: Path = Path(
        "policies/sources.threat_telemetry.yml"
    )
    passive_exposure_source_registry_path: Path = Path(
        "policies/sources.passive_exposure.yml"
    )
    passive_infrastructure_source_registry_path: Path = Path(
        "policies/sources.passive_infrastructure.yml"
    )
    advisory_source_registry_path: Path = Path("policies/sources.advisories.yml")
    corporate_change_source_registry_path: Path = Path(
        "policies/sources.corporate_changes.yml"
    )
    relationship_source_registry_path: Path = Path("policies/sources.relationships.yml")
    conditional_integration_source_registry_path: Path = Path(
        "policies/sources.conditional_integrations.yml"
    )
    ats_source_registry_path: Path = Path("policies/sources.ats_expansion.yml")
    provider_onboarding_registry_path: Path = Path("policies/provider_onboarding.yml")
    source_portfolio_path: Path = Path("policies/source_portfolio.yml")
    company_identity_expansion_source_portfolio_path: Path = Path(
        "policies/source_portfolio.company_identity_expansion.yml"
    )
    decp_source_portfolio_path: Path = Path("policies/source_portfolio.decp.yml")
    procurement_funding_source_portfolio_path: Path = Path(
        "policies/source_portfolio.procurement_funding.yml"
    )
    public_web_source_portfolio_path: Path = Path(
        "policies/source_portfolio.public_web.yml"
    )
    vulnerability_source_portfolio_path: Path = Path(
        "policies/source_portfolio.vulnerability.yml"
    )
    search_archive_source_portfolio_path: Path = Path(
        "policies/source_portfolio.search_archives.yml"
    )
    incident_source_portfolio_path: Path = Path(
        "policies/source_portfolio.incidents.yml"
    )
    threat_telemetry_source_portfolio_path: Path = Path(
        "policies/source_portfolio.threat_telemetry.yml"
    )
    passive_exposure_source_portfolio_path: Path = Path(
        "policies/source_portfolio.passive_exposure.yml"
    )
    passive_infrastructure_source_portfolio_path: Path = Path(
        "policies/source_portfolio.passive_infrastructure.yml"
    )
    advisory_source_portfolio_path: Path = Path(
        "policies/source_portfolio.advisories.yml"
    )
    corporate_change_source_portfolio_path: Path = Path(
        "policies/source_portfolio.corporate_changes.yml"
    )
    relationship_source_portfolio_path: Path = Path(
        "policies/source_portfolio.relationships.yml"
    )
    conditional_integration_source_portfolio_path: Path = Path(
        "policies/source_portfolio.conditional_integrations.yml"
    )
    ats_source_portfolio_path: Path = Path("policies/source_portfolio.ats_expansion.yml")
    source_activation_path: Path = Path("policies/source_activation.yml")
    greenhouse_board_registry_path: Path = Path("policies/greenhouse_boards.yml")
    lever_site_registry_path: Path = Path("policies/lever_sites.yml")
    smartrecruiters_company_registry_path: Path = Path(
        "policies/smartrecruiters_companies.yml"
    )
    ashby_board_registry_path: Path = Path("policies/ashby_boards.yml")
    recruitee_site_registry_path: Path = Path("policies/recruitee_sites.yml")
    teamtailor_account_registry_path: Path = Path("policies/teamtailor_accounts.yml")
    organization_identity_target_registry_path: Path = Path(
        "policies/organization_identity_targets.yml"
    )
    public_web_target_registry_path: Path = Path("policies/public_web_targets.yml")
    developer_ecosystem_target_registry_path: Path = Path(
        "policies/developer_ecosystem_targets.yml"
    )
    search_query_template_registry_path: Path = Path(
        "policies/search_query_templates.yml"
    )
    github_code_search_template_registry_path: Path = Path(
        "policies/github_code_search_templates.yml"
    )
    crossref_publication_target_registry_path: Path = Path(
        "policies/crossref_publication_targets.yml"
    )
    patentsview_patent_target_registry_path: Path = Path(
        "policies/patentsview_patent_targets.yml"
    )
    w3c_affiliation_target_registry_path: Path = Path(
        "policies/w3c_affiliation_targets.yml"
    )
    mojeek_search_entitlement_registry_path: Path = Path(
        "policies/mojeek_search_entitlement.yml"
    )
    marginalia_search_entitlement_registry_path: Path = Path(
        "policies/marginalia_search_entitlement.yml"
    )
    vulnerability_query_target_registry_path: Path = Path(
        "policies/vulnerability_query_targets.yml"
    )
    passive_infrastructure_target_registry_path: Path = Path(
        "policies/passive_infrastructure_targets.yml"
    )
    rdap_target_registry_path: Path = Path("policies/rdap_targets.yml")
    sec_incident_target_registry_path: Path = Path("policies/sec_incident_targets.yml")
    retention_policy_path: Path = Path("policies/retention.yml")
    collection_schedule_path: Path = Path("policies/collection_schedules.yml")
    decp_collection_schedule_path: Path = Path("policies/collection_schedules.decp.yml")
    procurement_funding_collection_schedule_path: Path = Path(
        "policies/collection_schedules.procurement_funding.yml"
    )
    public_web_collection_schedule_path: Path = Path(
        "policies/collection_schedules.public_web.yml"
    )
    vulnerability_collection_schedule_path: Path = Path(
        "policies/collection_schedules.vulnerability.yml"
    )
    search_archive_collection_schedule_path: Path = Path(
        "policies/collection_schedules.search_archives.yml"
    )
    passive_infrastructure_collection_schedule_path: Path = Path(
        "policies/collection_schedules.passive_infrastructure.yml"
    )
    incident_collection_schedule_path: Path = Path(
        "policies/collection_schedules.incidents.yml"
    )
    threat_telemetry_collection_schedule_path: Path = Path(
        "policies/collection_schedules.threat_telemetry.yml"
    )
    ats_collection_schedule_path: Path = Path(
        "policies/collection_schedules.ats_expansion.yml"
    )
    sec_edgar_user_agent: str | None = Field(default=None, max_length=300)
    phishtank_user_agent: str | None = Field(default=None, max_length=300)
    control_plane_token: str = Field(
        default="development-control-token",
        min_length=16,
        max_length=500,
    )
    scheduler_poll_seconds: float = Field(default=5.0, gt=0, le=300)
    worker_poll_seconds: float = Field(default=2.0, gt=0, le=300)
    source_http_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)


@lru_cache
def get_settings() -> Settings:
    return Settings()

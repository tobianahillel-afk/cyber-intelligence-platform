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
    decp_source_registry_path: Path = Path("policies/sources.decp.yml")
    public_web_source_registry_path: Path = Path("policies/sources.public_web.yml")
    vulnerability_source_registry_path: Path = Path(
        "policies/sources.vulnerability.yml"
    )
    incident_source_registry_path: Path = Path("policies/sources.incidents.yml")
    provider_onboarding_registry_path: Path = Path("policies/provider_onboarding.yml")
    source_portfolio_path: Path = Path("policies/source_portfolio.yml")
    decp_source_portfolio_path: Path = Path("policies/source_portfolio.decp.yml")
    public_web_source_portfolio_path: Path = Path(
        "policies/source_portfolio.public_web.yml"
    )
    vulnerability_source_portfolio_path: Path = Path(
        "policies/source_portfolio.vulnerability.yml"
    )
    incident_source_portfolio_path: Path = Path(
        "policies/source_portfolio.incidents.yml"
    )
    greenhouse_board_registry_path: Path = Path("policies/greenhouse_boards.yml")
    lever_site_registry_path: Path = Path("policies/lever_sites.yml")
    smartrecruiters_company_registry_path: Path = Path(
        "policies/smartrecruiters_companies.yml"
    )
    organization_identity_target_registry_path: Path = Path(
        "policies/organization_identity_targets.yml"
    )
    public_web_target_registry_path: Path = Path("policies/public_web_targets.yml")
    retention_policy_path: Path = Path("policies/retention.yml")
    collection_schedule_path: Path = Path("policies/collection_schedules.yml")
    decp_collection_schedule_path: Path = Path("policies/collection_schedules.decp.yml")
    public_web_collection_schedule_path: Path = Path(
        "policies/collection_schedules.public_web.yml"
    )
    control_plane_token: str = Field(
        default="development-control-token",
        min_length=16,
        max_length=500,
    )
    scheduler_poll_seconds: float = Field(default=5.0, gt=0, le=300)
    worker_poll_seconds: float = Field(default=2.0, gt=0, le=300)
    source_http_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65_535)
    api_reload: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

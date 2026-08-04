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
    greenhouse_board_registry_path: Path = Path("policies/greenhouse_boards.yml")
    lever_site_registry_path: Path = Path("policies/lever_sites.yml")
    smartrecruiters_company_registry_path: Path = Path(
        "policies/smartrecruiters_companies.yml"
    )
    retention_policy_path: Path = Path("policies/retention.yml")
    collection_schedule_path: Path = Path("policies/collection_schedules.yml")
    scheduler_poll_seconds: float = Field(default=5.0, gt=0, le=300)
    worker_poll_seconds: float = Field(default=2.0, gt=0, le=300)
    source_http_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65_535)
    api_reload: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

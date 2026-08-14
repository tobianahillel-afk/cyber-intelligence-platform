from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PublicWebCrawlRuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CIP_AUTOMATIC_PUBLIC_WEB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    crawl_deadline_seconds: int = Field(default=300, ge=1, le=3_600)
    max_crawl_concurrency: int = Field(default=1, ge=1, le=16)

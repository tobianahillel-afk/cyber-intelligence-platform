from __future__ import annotations

from datetime import datetime

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PublicWebBrowserFallbackSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CIP_AUTOMATIC_PUBLIC_WEB_BROWSER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = False
    authorization_reference: str | None = Field(default=None, max_length=500)
    reviewed_at: datetime | None = None
    expires_at: datetime | None = None
    min_static_text_chars: int = Field(default=200, ge=1, le=100_000)
    max_pages: int = Field(default=3, ge=1, le=25)

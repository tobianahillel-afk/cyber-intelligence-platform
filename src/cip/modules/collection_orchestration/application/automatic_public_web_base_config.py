from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from cip.adapters.sources.public_web.provisioning import AutomaticPublicWebPolicy


@dataclass(frozen=True, slots=True)
class AutomaticPublicWebBaseConfig:
    enabled: bool = False
    organization_ids: tuple[UUID, ...] = ()
    authorization_reference: str | None = None
    reviewed_at: datetime | None = None
    expires_at: datetime | None = None
    refresh_interval_seconds: int = 86_400
    max_link_depth: int = 1
    max_pages: int = 100
    max_total_bytes: int = 10_000_000
    max_resource_bytes: int = 1_000_000
    max_redirects: int = 3

    def policy(self) -> AutomaticPublicWebPolicy | None:
        if not self.enabled:
            return None
        if not self.organization_ids:
            raise ValueError("automatic public web requires approved organization ids")
        if self.authorization_reference is None:
            raise ValueError("automatic public web requires an authorization reference")
        if self.reviewed_at is None:
            raise ValueError("automatic public web requires an authorization review time")
        return AutomaticPublicWebPolicy(
            authorization_reference=self.authorization_reference,
            reviewed_at=self.reviewed_at,
            expires_at=self.expires_at,
            refresh_interval_seconds=self.refresh_interval_seconds,
            max_link_depth=self.max_link_depth,
            max_pages=self.max_pages,
            max_total_bytes=self.max_total_bytes,
            max_resource_bytes=self.max_resource_bytes,
            max_redirects=self.max_redirects,
        )

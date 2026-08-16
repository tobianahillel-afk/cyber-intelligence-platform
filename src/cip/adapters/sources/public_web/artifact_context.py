from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

import httpx

from cip.adapters.sources.public_web.artifact_policy import BrowserArtifactLimits
from cip.modules.public_footprint.application.artifact_storage import ArtifactStore
from cip.shared.kernel.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class BrowserArtifactExecutionContext:
    job_id: UUID
    retention_until: datetime
    download_client: httpx.Client
    store: ArtifactStore | None = None
    limits: BrowserArtifactLimits = field(default_factory=BrowserArtifactLimits)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "retention_until",
            require_aware_utc(self.retention_until, field_name="retention_until"),
        )

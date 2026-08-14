from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import httpx


@dataclass(frozen=True, slots=True)
class PublicWebFallbackRunContext:
    collection_job_id: UUID
    collected_at: datetime
    retention_until: datetime
    timeout_seconds: float
    transport: httpx.BaseTransport | None
    adapter_id: str

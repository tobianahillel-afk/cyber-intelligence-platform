from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from cip.modules.source_portfolio.domain.models import CatalogStatus, FreshnessState
from cip.modules.source_portfolio.infrastructure.models import (
    SourceHealthRecord,
    SourcePortfolioRecord,
)
from cip.modules.source_portfolio.infrastructure.persistence_time import persistence_utc
from cip.shared.kernel.time import require_aware_utc


def source_execution_allowed(
    session: Session,
    source_id: str,
    *,
    now: datetime,
) -> bool:
    """Return whether a queued or scheduled source may execute now.

    Sources not yet represented in the lot-10 portfolio keep the legacy behavior.
    """

    current = require_aware_utc(now, field_name="now")
    record = session.get(SourcePortfolioRecord, source_id)
    if record is None:
        return True
    if record.status != CatalogStatus.EXECUTABLE.value:
        return False
    expires_at = persistence_utc(record.authorization_expires_at)
    if expires_at is None or expires_at > current:
        return True
    health = session.get(SourceHealthRecord, source_id)
    if health is not None:
        health.freshness_state = FreshnessState.AUTHORIZATION_EXPIRED.value
        health.updated_at = current
    return False

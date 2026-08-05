from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from cip.modules.source_portfolio.application.health import refresh_freshness
from cip.modules.source_portfolio.domain.models import CatalogStatus, FreshnessState
from cip.modules.source_portfolio.infrastructure.models import SourcePortfolioRecord
from cip.shared.kernel.time import require_aware_utc

BLOCKING_FRESHNESS_STATES = frozenset(
    {
        FreshnessState.AUTHORIZATION_EXPIRED,
        FreshnessState.QUOTA_EXHAUSTED,
        FreshnessState.COST_BUDGET_EXHAUSTED,
    }
)


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
    health = refresh_freshness(session, source_id, now=current)
    return health.freshness_state not in BLOCKING_FRESHNESS_STATES

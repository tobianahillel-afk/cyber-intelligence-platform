from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from cip.adapters.sources.sherlock_local.adapter import SherlockLocalAdapter
from cip.adapters.sources.sherlock_local.registry import SherlockTarget
from cip.modules.professional_context.infrastructure.community_persistence import (
    persist_community_context,
)
from cip.modules.professional_context.infrastructure.context_models import (
    ProfessionalCommunityRecord,
)


def execute_sherlock_target(
    session: Session,
    adapter: SherlockLocalAdapter,
    target: SherlockTarget,
    *,
    now: datetime,
) -> tuple[ProfessionalCommunityRecord, ...]:
    contexts = adapter.collect(target, observed_at=now)
    if not contexts:
        return ()
    return persist_community_context(session, contexts, now=now)

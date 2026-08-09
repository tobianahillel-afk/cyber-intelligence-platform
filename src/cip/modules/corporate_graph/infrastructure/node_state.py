from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.corporate_graph.domain.reconciliation import reconcile_node_snapshots
from cip.modules.corporate_graph.infrastructure.models import (
    CorporateGraphNodeRecord,
    EntityResolutionBindingRecord,
)
from cip.modules.corporate_graph.infrastructure.projection_hydration import node_snapshots


def refresh_node_state(session: Session, node_id: UUID, *, now: datetime) -> None:
    record = session.get(CorporateGraphNodeRecord, node_id)
    if record is None:
        raise ValueError("graph node disappeared during reconciliation")
    projection = reconcile_node_snapshots(node_snapshots(session, node_id), now=now)
    binding = session.scalar(
        select(EntityResolutionBindingRecord).where(
            EntityResolutionBindingRecord.node_key == record.node_key,
            EntityResolutionBindingRecord.current.is_(True),
        )
    )
    record.display_name = projection.display_name
    record.organization_id = (
        binding.organization_id if binding is not None else projection.organization_id
    )
    record.source_count = projection.source_count
    record.confidence = projection.confidence
    record.current = projection.current
    record.suppressed = projection.suppressed
    record.first_observed_at = projection.first_observed_at
    record.last_observed_at = projection.last_observed_at
    record.updated_at = now

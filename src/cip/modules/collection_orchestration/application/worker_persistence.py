from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from cip.modules.collection_orchestration.application.ports import AdapterCollectionBatch
from cip.modules.corporate_changes.infrastructure.projections import persist_change_claims
from cip.modules.incident_intelligence.infrastructure.projections import persist_incident_claims
from cip.modules.opportunities.infrastructure.projections import persist_commercial_projections
from cip.modules.organizations.infrastructure.identity_claims import persist_identity_claims
from cip.modules.organizations.infrastructure.identity_persistence import (
    persist_identity_projections,
)
from cip.modules.organizations.infrastructure.persistence import upsert_organizations
from cip.modules.passive_exposure.infrastructure.projections import persist_passive_snapshots
from cip.modules.procurement_history.infrastructure.projections import (
    persist_procurement_projections,
)
from cip.modules.public_footprint.infrastructure.projections import (
    persist_public_footprint_projections,
)
from cip.modules.source_portfolio.application.service import (
    CollectionHealthUpdate,
    SourcePortfolioNotFoundError,
    record_collection_failure,
    record_collection_success,
)
from cip.modules.source_portfolio.domain.models import SchemaState
from cip.modules.threat_telemetry.infrastructure.projections import persist_indicator_snapshots
from cip.modules.vulnerability_knowledge.infrastructure.projections import (
    persist_vulnerability_snapshots,
)


def persist_batch_projections(
    session: Session,
    batch: AdapterCollectionBatch,
    *,
    now: datetime,
) -> None:
    persist_identity_projections(session, batch.identity_projections, now=now)
    persist_identity_claims(session, batch.identity_projections)
    persist_commercial_projections(session, batch.commercial_projections, now=now)
    upsert_organizations(session, batch.procurement_organizations)
    persist_procurement_projections(session, batch.procurement_projections, now=now)
    persist_public_footprint_projections(
        session,
        batch.public_footprint_projections,
        now=now,
    )
    persist_vulnerability_snapshots(session, batch.vulnerability_snapshots, now=now)
    persist_passive_snapshots(session, batch.passive_exposure_projections, now=now)
    persist_incident_claims(session, batch.incident_claims, now=now)
    persist_change_claims(session, batch.corporate_change_claims, now=now)
    persist_indicator_snapshots(session, batch.threat_indicator_snapshots, now=now)


def record_success_health(
    session: Session,
    source_id: str,
    batch: AdapterCollectionBatch,
    *,
    now: datetime,
) -> None:
    source_record_at = max(
        (
            observation.source_updated_at or observation.observed_at or observation.collected_at
            for observation in batch.observations
        ),
        default=None,
    )
    try:
        record_collection_success(
            session,
            source_id,
            CollectionHealthUpdate(
                source_record_at=source_record_at,
                schema_state=SchemaState.STABLE,
                quota_remaining=batch.quota_remaining,
                cost=batch.request_cost,
                observations=batch.observations,
                not_modified=batch.not_modified,
                operational_metrics=_operational_payload(batch),
            ),
            now=now,
        )
    except SourcePortfolioNotFoundError:
        return


def record_failure_health(
    session: Session,
    source_id: str,
    *,
    error_code: str,
    now: datetime,
    batch: AdapterCollectionBatch | None = None,
) -> None:
    try:
        record_collection_failure(
            session,
            source_id,
            error_code=error_code,
            schema_drift=error_code == "source_schema_drift",
            now=now,
            operational_metrics=(
                _operational_payload(batch) if batch is not None else None
            ),
        )
    except SourcePortfolioNotFoundError:
        return


def _operational_payload(batch: AdapterCollectionBatch) -> dict[str, object] | None:
    metrics = batch.operational_metrics
    return metrics.as_payload() if metrics is not None else None

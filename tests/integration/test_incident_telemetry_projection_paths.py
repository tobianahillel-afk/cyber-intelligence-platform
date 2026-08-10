from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from uuid import UUID

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    CollectionAdapter,
)
from cip.modules.collection_orchestration.application.worker import WorkerStatus, run_worker_once
from cip.modules.collection_orchestration.domain.models import CollectionJob, SourceSchedule
from cip.modules.collection_orchestration.infrastructure.repository import enqueue_job
from cip.modules.data_governance.domain.retention import RetentionPolicy, RetentionRule
from cip.modules.incident_intelligence.domain.models import (
    IncidentClaimSnapshot,
    IncidentClaimType,
    IncidentSourceKind,
    IncidentType,
    OrganizationLinkStatus,
)
from cip.modules.incident_intelligence.infrastructure.models import (
    IncidentClaimSnapshotRecord,
    IncidentRecord,
)
from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.raw_observations.infrastructure.models import RawObservationRecord
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.modules.source_portfolio.application.backfill_worker import (
    BackfillWorkerStatus,
    run_backfill_once,
)
from cip.modules.source_portfolio.application.service import request_backfill, sync_source_portfolio
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio
from cip.modules.threat_telemetry.domain.models import (
    IndicatorSnapshot,
    IndicatorState,
    IndicatorType,
    SensorScope,
    TelemetrySourceKind,
)
from cip.modules.threat_telemetry.infrastructure.models import (
    ThreatIndicatorRecord,
    ThreatIndicatorSnapshotRecord,
)
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import session_scope

NOW = datetime(2026, 8, 9, 23, 30, tzinfo=UTC)


class IntelligenceProjectionAdapter:
    source_id = "reference-synthetic"
    adapter_id = "reference-synthetic-adapter"
    data_category = DataCategory.PUBLIC_RESULT_METADATA

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch:
        del checkpoint_payload
        record_key = f"intelligence-{collection_job_id}"
        observation = RawObservation(
            source_id=self.source_id,
            adapter_id=self.adapter_id,
            adapter_version="1",
            collection_job_id=collection_job_id,
            source_record_type="intelligence_reference",
            source_record_key=record_key,
            source_url=f"https://example.invalid/{record_key}",
            payload_hash_sha256="8" * 64,
            data_categories=frozenset({self.data_category}),
            collected_at=collected_at,
            observed_at=collected_at,
            published_at=collected_at,
            source_updated_at=collected_at,
            schema_fingerprint="intelligence-reference-v1",
            retention_until=retention_until,
        )
        incident = IncidentClaimSnapshot(
            source_id=self.source_id,
            source_kind=IncidentSourceKind.RESEARCH,
            source_record_key=record_key,
            source_url=f"https://example.invalid/{record_key}",
            incident_key=f"incident:{collection_job_id}",
            claim_type=IncidentClaimType.RESEARCHER_REPORT,
            incident_type=IncidentType.UNKNOWN,
            title="Synthetic incident metadata",
            summary="Synthetic metadata used only to validate collection persistence.",
            claimed_organization_name=None,
            organization_id=None,
            organization_link_status=OrganizationLinkStatus.UNRESOLVED,
            published_at=collected_at,
            modified_at=collected_at,
        )
        indicator = IndicatorSnapshot(
            source_id=self.source_id,
            source_kind=TelemetrySourceKind.PHISHING_FEED,
            source_record_key=record_key,
            source_url=f"https://example.invalid/{record_key}",
            indicator_type=IndicatorType.URL,
            indicator_value="https://phish.example.net/login",
            state=IndicatorState.MALICIOUS,
            published_at=collected_at,
            modified_at=collected_at,
            first_seen_at=collected_at,
            last_seen_at=collected_at,
            expires_at=collected_at + timedelta(hours=2),
            sensor_scope=SensorScope.PROVIDER_AGGREGATE,
            confidence=0.9,
            source_precedence=80,
        )
        return AdapterCollectionBatch(
            observations=(observation,),
            checkpoint_payload={"sequence": 1},
            not_modified=False,
            incident_claims=(incident,),
            threat_indicator_snapshots=(indicator,),
        )


def test_incremental_worker_persists_incident_and_telemetry_projections() -> None:
    factory = _factory()
    adapter = IntelligenceProjectionAdapter()
    _seed_source(factory)
    with session_scope(factory) as session:
        job = CollectionJob.from_schedule(
            SourceSchedule(adapter.source_id, adapter.adapter_id, 300),
            scheduled_for=NOW,
        )
        assert enqueue_job(session, job) is True

    outcome = run_worker_once(
        factory,
        worker_id="intelligence-worker",
        adapters={(adapter.source_id, adapter.adapter_id): cast(CollectionAdapter, adapter)},
        retention_policy=_retention_policy(),
        clock=lambda: NOW + timedelta(seconds=1),
    )

    assert outcome.status is WorkerStatus.SUCCEEDED
    assert outcome.observations_written == 1
    _assert_projection_writes(factory)


def test_backfill_worker_persists_incident_and_telemetry_projections() -> None:
    factory = _factory()
    adapter = IntelligenceProjectionAdapter()
    _seed_source(factory)
    with session_scope(factory) as session:
        request_backfill(
            session,
            adapter.source_id,
            (("2026-01-01", "2026-02-01"),),
            actor="intelligence-backfill-test",
            now=NOW,
        )

    outcome = run_backfill_once(
        factory,
        worker_id="intelligence-backfill-worker",
        adapters={(adapter.source_id, adapter.adapter_id): cast(CollectionAdapter, adapter)},
        retention_policy=_retention_policy(),
        clock=lambda: NOW + timedelta(seconds=1),
    )

    assert outcome.status is BackfillWorkerStatus.SUCCEEDED
    assert outcome.observations_written == 1
    _assert_projection_writes(factory)


def _assert_projection_writes(factory: sessionmaker[Session]) -> None:
    with factory() as session:
        assert session.scalar(select(func.count(RawObservationRecord.id))) == 1
        assert session.scalar(select(func.count(IncidentRecord.id))) == 1
        assert session.scalar(select(func.count(IncidentClaimSnapshotRecord.id))) == 1
        assert session.scalar(select(func.count(ThreatIndicatorRecord.id))) == 1
        assert session.scalar(select(func.count(ThreatIndicatorSnapshotRecord.id))) == 1


def _seed_source(factory: sessionmaker[Session]) -> None:
    with session_scope(factory) as session:
        session.add(_source_record())
        sync_source_portfolio(
            session,
            load_source_portfolio(Path("policies/source_portfolio.yml")),
            now=NOW,
        )


def _factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    get_metadata().create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def _source_record() -> SourceRecord:
    return SourceRecord(
        id="reference-synthetic",
        name="Synthetic reference adapter",
        base_url="https://example.invalid/source-portfolio-reference",
        status="enabled",
        source_type="api",
        owner="Cyber Intelligence Platform",
        terms_url=None,
        licence=None,
        allowed_data_categories=[DataCategory.PUBLIC_RESULT_METADATA.value],
        prohibited_data_categories=[],
        rate_limit_per_minute=None,
        retention_days=30,
        attribution_required=False,
        raw_content_storage=False,
        human_review_required=False,
        authorization_status="approved",
        authorization_document_reference="TEST-REFERENCE",
        authorization_reviewed_at=NOW,
        authorization_expires_at=NOW + timedelta(days=365),
        approved_hosts=["example.invalid"],
        approved_path_prefixes=["/source-portfolio-reference"],
        approved_purposes=["runtime-contract-validation"],
        automated_collection_allowed=True,
        raw_storage_allowed=False,
    )


def _retention_policy() -> RetentionPolicy:
    return RetentionPolicy(
        version=1,
        rules={
            DataCategory.PUBLIC_RESULT_METADATA: RetentionRule(
                retention_days=30,
                review_interval_days=7,
            )
        },
        prohibited_categories=frozenset(),
        suppression_minimum_days=365,
        backup_deletion_propagation_max_days=30,
        restoration_requires_suppressions=True,
    )

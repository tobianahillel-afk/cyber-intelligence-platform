from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.modules.collection_orchestration.application.reference_adapter import (
    ReferencePortfolioAdapter,
)
from cip.modules.collection_orchestration.application.worker import (
    WorkerStatus,
    run_worker_once,
)
from cip.modules.collection_orchestration.domain.models import (
    CollectionJob,
    SourceSchedule,
)
from cip.modules.collection_orchestration.infrastructure.repository import enqueue_job
from cip.modules.data_governance.domain.retention import RetentionPolicy, RetentionRule
from cip.modules.raw_observations.infrastructure.models import RawObservationRecord
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.modules.source_portfolio.application.service import (
    get_source_health,
    sync_source_portfolio,
)
from cip.modules.source_portfolio.domain.models import (
    AnomalyState,
    FreshnessState,
    SchemaState,
)
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import session_scope

NOW = datetime(2026, 8, 5, 0, 0, tzinfo=UTC)


def test_reference_worker_writes_observation_checkpoint_and_health() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    get_metadata().create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    entries = load_source_portfolio(Path("policies/source_portfolio.yml"))

    with session_scope(factory) as session:
        session.add(_source_record())
        sync_source_portfolio(session, entries, now=NOW)
        schedule = SourceSchedule(
            source_id="reference-synthetic",
            adapter_id="reference-synthetic-adapter",
            interval_seconds=300,
        )
        job = CollectionJob.from_schedule(schedule, scheduled_for=NOW)
        assert enqueue_job(session, job) is True

    adapter = ReferencePortfolioAdapter()
    outcome = run_worker_once(
        factory,
        worker_id="vertical-worker",
        adapters={(adapter.source_id, adapter.adapter_id): adapter},
        retention_policy=_retention_policy(),
        clock=lambda: NOW + timedelta(seconds=1),
    )

    assert outcome.status is WorkerStatus.SUCCEEDED
    assert outcome.observations_written == 1
    with Session(engine) as session:
        observation = session.scalar(select(RawObservationRecord))
        assert observation is not None
        assert observation.source_id == "reference-synthetic"
        assert observation.source_record_key == "1"
        health = get_source_health(session, "reference-synthetic")
        assert health.freshness_state is FreshnessState.FRESH
        assert health.schema_state is SchemaState.STABLE
        assert health.volume_state is AnomalyState.NORMAL
        assert health.field_population_state is AnomalyState.NORMAL
        assert health.circuit_state == "closed"
        assert health.last_source_record_at == NOW + timedelta(seconds=1)


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

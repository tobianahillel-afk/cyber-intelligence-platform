from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.modules.collection_orchestration.application.reference_adapter import (
    ReferencePortfolioAdapter,
)
from cip.modules.collection_orchestration.application.runtime import (
    CollectionRuntime,
    run_scheduler_once,
)
from cip.modules.collection_orchestration.application.worker import (
    WorkerStatus,
    run_worker_once,
)
from cip.modules.collection_orchestration.domain.models import CollectionJob, SourceSchedule
from cip.modules.collection_orchestration.infrastructure.models import CollectionJobRecord
from cip.modules.collection_orchestration.infrastructure.repository import enqueue_job
from cip.modules.data_governance.domain.retention import RetentionPolicy, RetentionRule
from cip.modules.raw_observations.infrastructure.models import RawObservationRecord
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.modules.source_portfolio.application.service import (
    get_source_health,
    pause_source,
    sync_source_portfolio,
)
from cip.modules.source_portfolio.domain.models import FreshnessState
from cip.modules.source_portfolio.infrastructure.models import SourcePortfolioRecord
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import session_scope

NOW = datetime(2026, 8, 5, tzinfo=UTC)


def test_worker_cancels_job_when_source_was_paused_after_queueing() -> None:
    factory = _factory()
    adapter = ReferencePortfolioAdapter()
    with session_scope(factory) as session:
        session.add(_source_record())
        entries = load_source_portfolio(Path("policies/source_portfolio.yml"))
        sync_source_portfolio(session, entries, now=NOW)
        schedule = SourceSchedule(
            source_id=adapter.source_id,
            adapter_id=adapter.adapter_id,
            interval_seconds=300,
        )
        assert enqueue_job(session, CollectionJob.from_schedule(schedule, scheduled_for=NOW))
        pause_source(session, adapter.source_id, actor="guard-test", now=NOW)

    outcome = run_worker_once(
        factory,
        worker_id="guard-worker",
        adapters={(adapter.source_id, adapter.adapter_id): adapter},
        retention_policy=_retention_policy(),
        clock=lambda: NOW + timedelta(seconds=1),
    )

    assert outcome.status is WorkerStatus.CANCELLED
    with factory() as session:
        job = session.scalar(select(CollectionJobRecord))
        assert job is not None
        assert job.status == "cancelled"
        assert session.scalar(select(func.count(RawObservationRecord.id))) == 0


def test_scheduler_skips_expired_authorization_and_updates_health() -> None:
    factory = _factory()
    entries = load_source_portfolio(Path("policies/source_portfolio.yml"))
    with session_scope(factory) as session:
        session.add(_source_record())
        sync_source_portfolio(session, entries, now=NOW)
        portfolio = session.get(SourcePortfolioRecord, "reference-synthetic")
        assert portfolio is not None
        portfolio.authorization_expires_at = NOW - timedelta(seconds=1)

    adapter = ReferencePortfolioAdapter()
    schedule = SourceSchedule(
        source_id=adapter.source_id,
        adapter_id=adapter.adapter_id,
        interval_seconds=300,
    )
    runtime = CollectionRuntime(
        factory=factory,
        schedules=(schedule,),
        adapters={(adapter.source_id, adapter.adapter_id): adapter},
        retention_policy=_retention_policy(),
        portfolio=entries,
    )

    assert run_scheduler_once(runtime, now=NOW) == 0
    with factory() as session:
        assert session.scalar(select(func.count(CollectionJobRecord.id))) == 0
        health = get_source_health(session, "reference-synthetic")
        assert health.freshness_state is FreshnessState.AUTHORIZATION_EXPIRED


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

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    AdapterOperationalMetrics,
    AdapterPartialExecutionError,
)
from cip.modules.collection_orchestration.application.reference_adapter import (
    ReferencePortfolioAdapter,
)
from cip.modules.collection_orchestration.application.worker import (
    WorkerStatus,
    run_worker_once,
)
from cip.modules.collection_orchestration.domain.models import CollectionJob, SourceSchedule
from cip.modules.collection_orchestration.infrastructure.models import (
    CollectionCheckpointRecord,
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
from cip.modules.source_portfolio.infrastructure.models import SourceValueEventRecord
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import session_scope

NOW = datetime(2026, 8, 16, 0, 0, tzinfo=UTC)


class PartialThenSuccessfulAdapter:
    source_id = ReferencePortfolioAdapter.source_id
    adapter_id = ReferencePortfolioAdapter.adapter_id
    data_category = ReferencePortfolioAdapter.data_category

    def __init__(self) -> None:
        self._reference = ReferencePortfolioAdapter()
        self._calls = 0

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch:
        self._calls += 1
        batch = self._reference.collect(
            collection_job_id=collection_job_id,
            checkpoint_payload=None,
            collected_at=collected_at,
            retention_until=retention_until,
        )
        batch = replace(
            batch,
            operational_metrics=AdapterOperationalMetrics(
                namespace="public_web.crawl.v1",
                values={
                    "attempted_pages": 2,
                    "fetched_pages": 1,
                    "deadline_exceeded": self._calls == 1,
                    "configured_concurrency": 2,
                    "effective_concurrency": 2,
                    "max_concurrency_used": 2,
                },
            ),
        )
        if self._calls == 1:
            raise AdapterPartialExecutionError(
                "whole-crawl deadline exceeded after partial progress",
                error_code="crawl_deadline_exceeded",
                retryable=True,
                batch=batch,
            )
        return batch


def test_partial_retry_persists_progress_without_double_counting() -> None:
    factory = _factory()
    adapter = PartialThenSuccessfulAdapter()
    with session_scope(factory) as session:
        session.add(_source_record())
        sync_source_portfolio(
            session,
            load_source_portfolio(Path("policies/source_portfolio.yml")),
            now=NOW,
        )
        schedule = SourceSchedule(
            source_id=adapter.source_id,
            adapter_id=adapter.adapter_id,
            interval_seconds=300,
        )
        assert enqueue_job(
            session,
            CollectionJob.from_schedule(schedule, scheduled_for=NOW),
        )

    first = run_worker_once(
        factory,
        worker_id="sa16-l12-partial-worker",
        adapters={(adapter.source_id, adapter.adapter_id): adapter},
        retention_policy=_retention_policy(),
        clock=lambda: NOW + timedelta(seconds=1),
    )
    assert first.status is WorkerStatus.RETRY_SCHEDULED
    assert first.observations_written == 1
    assert first.error_code == "crawl_deadline_exceeded"

    with factory() as session:
        assert _count(session, RawObservationRecord) == 1
        assert _count(session, SourceValueEventRecord) == 0
        checkpoint = session.get(
            CollectionCheckpointRecord,
            (adapter.source_id, adapter.adapter_id),
        )
        assert checkpoint is not None
        assert checkpoint.payload == {"sequence": 1}
        assert checkpoint.version == 1
        assert checkpoint.last_success_at is None
        health = get_source_health(session, adapter.source_id)
        assert health.last_success_at is None
        assert health.consecutive_failures == 1
        assert health.last_error_code == "crawl_deadline_exceeded"
        assert health.operational_metrics["namespace"] == "public_web.crawl.v1"
        values = health.operational_metrics["values"]
        assert isinstance(values, dict)
        assert values["deadline_exceeded"] is True
        assert values["max_concurrency_used"] == 2

    resumed = run_worker_once(
        factory,
        worker_id="sa16-l12-partial-worker",
        adapters={(adapter.source_id, adapter.adapter_id): adapter},
        retention_policy=_retention_policy(),
        clock=lambda: NOW + timedelta(seconds=32),
    )
    assert resumed.status is WorkerStatus.SUCCEEDED
    assert resumed.observations_written == 0

    with factory() as session:
        assert _count(session, RawObservationRecord) == 1
        assert _count(session, SourceValueEventRecord) == 1
        checkpoint = session.get(
            CollectionCheckpointRecord,
            (adapter.source_id, adapter.adapter_id),
        )
        assert checkpoint is not None
        assert checkpoint.payload == {"sequence": 1}
        assert checkpoint.version == 2
        assert _sqlite_utc(checkpoint.last_success_at) == NOW + timedelta(seconds=32)
        health = get_source_health(session, adapter.source_id)
        assert _sqlite_utc(health.last_success_at) == NOW + timedelta(seconds=32)
        assert health.consecutive_failures == 0
        assert health.last_error_code is None
        values = health.operational_metrics["values"]
        assert isinstance(values, dict)
        assert values["deadline_exceeded"] is False


def _sqlite_utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


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
        authorization_document_reference="TEST-SA16-L12",
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


def _factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    get_metadata().create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def _count(session: Session, record_type: type[object]) -> int:
    return int(session.scalar(select(func.count()).select_from(record_type)) or 0)

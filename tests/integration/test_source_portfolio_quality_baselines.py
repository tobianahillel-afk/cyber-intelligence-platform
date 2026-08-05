from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_portfolio.application.service import (
    CollectionHealthUpdate,
    get_source_health,
    record_collection_success,
    sync_source_portfolio,
)
from cip.modules.source_portfolio.domain.models import AnomalyState, SchemaState
from cip.modules.source_portfolio.infrastructure.models import SourceQualityBaselineRecord
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio
from cip.shared.persistence.metadata import get_metadata

NOW = datetime(2026, 8, 5, tzinfo=UTC)


def test_quality_baseline_detects_schema_volume_and_field_drift() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        sync_source_portfolio(
            session,
            load_source_portfolio(Path("policies/source_portfolio.yml")),
            now=NOW,
        )
        for sample in range(3):
            observations = tuple(
                _observation(index=sample * 10 + index, fingerprint="schema-v1")
                for index in range(10)
            )
            record_collection_success(
                session,
                "reference-synthetic",
                CollectionHealthUpdate(
                    source_record_at=NOW + timedelta(minutes=sample),
                    schema_state=SchemaState.STABLE,
                    quota_remaining=None,
                    cost=0,
                    observations=observations,
                ),
                now=NOW + timedelta(minutes=sample),
            )

        baseline = session.get(SourceQualityBaselineRecord, "reference-synthetic")
        assert baseline is not None
        assert baseline.sample_count == 3
        assert baseline.expected_records_per_run == 10.0

        health = record_collection_success(
            session,
            "reference-synthetic",
            CollectionHealthUpdate(
                source_record_at=NOW + timedelta(minutes=4),
                schema_state=SchemaState.STABLE,
                quota_remaining=None,
                cost=0,
                observations=(
                    _observation(
                        index=999,
                        fingerprint="schema-v2",
                        populated=False,
                    ),
                ),
            ),
            now=NOW + timedelta(minutes=4),
        )

        assert health.schema_state is SchemaState.DRIFTED
        assert health.volume_state is AnomalyState.ANOMALOUS
        assert health.field_population_state is AnomalyState.ANOMALOUS
        assert baseline.sample_count == 3


def test_not_modified_run_does_not_create_false_quality_alerts() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        sync_source_portfolio(
            session,
            load_source_portfolio(Path("policies/source_portfolio.yml")),
            now=NOW,
        )
        for sample in range(3):
            record_collection_success(
                session,
                "reference-synthetic",
                CollectionHealthUpdate(
                    source_record_at=NOW + timedelta(minutes=sample),
                    schema_state=SchemaState.STABLE,
                    quota_remaining=None,
                    cost=0,
                    observations=tuple(
                        _observation(index=sample * 10 + index, fingerprint="schema-v1")
                        for index in range(10)
                    ),
                ),
                now=NOW + timedelta(minutes=sample),
            )

        record_collection_success(
            session,
            "reference-synthetic",
            CollectionHealthUpdate(
                source_record_at=None,
                schema_state=SchemaState.STABLE,
                quota_remaining=None,
                cost=0,
                observations=(),
                not_modified=True,
            ),
            now=NOW + timedelta(minutes=4),
        )
        health = get_source_health(session, "reference-synthetic")

        assert health.schema_state is SchemaState.STABLE
        assert health.volume_state is AnomalyState.NORMAL
        assert health.field_population_state is AnomalyState.NORMAL


def _observation(
    *,
    index: int,
    fingerprint: str,
    populated: bool = True,
) -> RawObservation:
    return RawObservation(
        source_id="reference-synthetic",
        adapter_id="reference-synthetic-adapter",
        adapter_version="1.0.0",
        collection_job_id=uuid4(),
        source_record_type="reference_record",
        source_record_key=str(index) if populated else None,
        source_url=f"https://example.invalid/records/{index}",
        payload_hash_sha256=f"{index:064x}"[-64:],
        data_categories=frozenset({DataCategory.PUBLIC_RESULT_METADATA}),
        collected_at=NOW,
        observed_at=NOW if populated else None,
        payload_reference=f"memory://{index}" if populated else None,
        schema_fingerprint=fingerprint,
        content_language="en" if populated else None,
        retention_until=NOW + timedelta(days=30),
    )

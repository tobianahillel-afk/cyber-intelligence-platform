from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from cip.modules.collection_orchestration.infrastructure.models import CollectionJobRecord
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.modules.source_portfolio.application.service import (
    SourcePortfolioStateError,
    pause_source,
    request_priority_refresh,
    sync_source_portfolio,
)
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio
from cip.shared.persistence.metadata import get_metadata

NOW = datetime(2026, 8, 5, 0, 1, 30, tzinfo=UTC)


def test_priority_refresh_is_idempotent_per_minute() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        session.add(_source_record())
        sync_source_portfolio(
            session,
            load_source_portfolio(Path("policies/source_portfolio.yml")),
            now=NOW,
        )
        first = request_priority_refresh(
            session,
            "reference-synthetic",
            actor="priority-test",
            now=NOW,
        )
        second = request_priority_refresh(
            session,
            "reference-synthetic",
            actor="priority-test",
            now=NOW + timedelta(seconds=20),
        )

        assert first.created is True
        assert second.created is False
        assert second.job_id == first.job_id
        assert session.scalar(select(func.count(CollectionJobRecord.id))) == 1


def test_paused_source_rejects_priority_refresh() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        session.add(_source_record())
        sync_source_portfolio(
            session,
            load_source_portfolio(Path("policies/source_portfolio.yml")),
            now=NOW,
        )
        pause_source(
            session,
            "reference-synthetic",
            actor="priority-test",
            now=NOW,
        )

        with pytest.raises(SourcePortfolioStateError, match="not executable"):
            request_priority_refresh(
                session,
                "reference-synthetic",
                actor="priority-test",
                now=NOW,
            )


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

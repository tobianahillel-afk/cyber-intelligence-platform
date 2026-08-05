from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cip.modules.source_portfolio.application.service import (
    SourcePortfolioStateError,
    disable_source,
    enable_source,
    get_source_portfolio,
    pause_source,
    reconcile_runtime_adapters,
    resume_source,
    sync_source_portfolio,
)
from cip.modules.source_portfolio.domain.models import CatalogStatus
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio
from cip.shared.persistence.metadata import get_metadata

NOW = datetime(2026, 8, 5, tzinfo=UTC)


def test_target_dependent_source_tracks_real_runtime_adapter() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        entries = load_source_portfolio(Path("policies/source_portfolio.yml"))
        sync_source_portfolio(session, entries, now=NOW)

        assert get_source_portfolio(session, "recherche-entreprises").status is CatalogStatus.PAUSED
        reconciled = reconcile_runtime_adapters(
            session,
            {("recherche-entreprises", "recherche-entreprises-search")},
            now=NOW + timedelta(seconds=1),
        )
        assert "recherche-entreprises" in reconciled
        assert (
            get_source_portfolio(session, "recherche-entreprises").status
            is CatalogStatus.EXECUTABLE
        )

        reconcile_runtime_adapters(session, set(), now=NOW + timedelta(seconds=2))
        assert get_source_portfolio(session, "recherche-entreprises").status is CatalogStatus.PAUSED


def test_target_dependent_source_rejects_generic_pause_and_resume() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        entries = load_source_portfolio(Path("policies/source_portfolio.yml"))
        sync_source_portfolio(session, entries, now=NOW)

        with pytest.raises(SourcePortfolioStateError, match="runtime target reconciliation"):
            pause_source(
                session,
                "recherche-entreprises",
                actor="reconciliation-test",
                now=NOW,
            )
        with pytest.raises(SourcePortfolioStateError, match="runtime target reconciliation"):
            resume_source(
                session,
                "recherche-entreprises",
                actor="reconciliation-test",
                now=NOW + timedelta(seconds=1),
            )


def test_disable_is_not_undone_by_runtime_and_enable_waits_for_reconciliation() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        entries = load_source_portfolio(Path("policies/source_portfolio.yml"))
        sync_source_portfolio(session, entries, now=NOW)
        disable_source(
            session,
            "recherche-entreprises",
            actor="reconciliation-test",
            now=NOW,
        )
        reconcile_runtime_adapters(
            session,
            {("recherche-entreprises", "recherche-entreprises-search")},
            now=NOW + timedelta(seconds=1),
        )
        assert (
            get_source_portfolio(session, "recherche-entreprises").status
            is CatalogStatus.DISABLED
        )

        enabled = enable_source(
            session,
            "recherche-entreprises",
            actor="reconciliation-test",
            now=NOW + timedelta(seconds=2),
        )
        assert enabled.status is CatalogStatus.PAUSED
        reconcile_runtime_adapters(
            session,
            {("recherche-entreprises", "recherche-entreprises-search")},
            now=NOW + timedelta(seconds=3),
        )
        assert (
            get_source_portfolio(session, "recherche-entreprises").status
            is CatalogStatus.EXECUTABLE
        )

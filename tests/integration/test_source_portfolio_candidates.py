from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cip.modules.source_portfolio.application.candidates import (
    CatalogCandidateInput,
    import_catalog_candidates,
)
from cip.modules.source_portfolio.application.service import (
    SourcePortfolioStateError,
    get_source_portfolio,
    request_backfill,
)
from cip.modules.source_portfolio.domain.models import CatalogStatus
from cip.shared.persistence.metadata import get_metadata

NOW = datetime(2026, 8, 5, tzinfo=UTC)


def test_imported_candidates_are_deterministic_and_non_executable() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        candidate = CatalogCandidateInput(
            display_name="Example OSINT candidate",
            canonical_url="https://example.test/osint-tool",
            category="public_research_tool",
            metadata={"upstream_path": "Search Engines/General"},
        )
        first = import_catalog_candidates(
            session,
            "osint-framework",
            (candidate,),
            now=NOW,
        )
        second = import_catalog_candidates(
            session,
            "osint-framework",
            (candidate,),
            now=NOW,
        )

        assert first == second
        entry = get_source_portfolio(session, first[0])
        assert entry.status is CatalogStatus.CANDIDATE
        assert entry.executable is False
        assert entry.metadata["authorization_required"] is True

        try:
            request_backfill(
                session,
                entry.source_id,
                (("a", "b"),),
                actor="candidate-test",
                now=NOW,
            )
        except SourcePortfolioStateError as exc:
            assert "cannot execute" in str(exc)
        else:
            raise AssertionError("imported candidate unexpectedly executed")

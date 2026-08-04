from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cip.adapters.sources.greenhouse.mapper import map_greenhouse_job
from cip.adapters.sources.greenhouse.registry import GreenhouseBoard
from cip.adapters.sources.greenhouse.schemas import GreenhouseJob
from cip.modules.evidence.infrastructure.models import EvidenceRecord
from cip.modules.opportunities.infrastructure.models import (
    CommercialSignalRecord,
    OpportunityRecord,
)
from cip.modules.opportunities.infrastructure.projections import (
    persist_commercial_projections,
)
from cip.modules.opportunities.infrastructure.queries import get_opportunity_detail
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)
BOARD = GreenhouseBoard(
    id="example",
    board_token="example",
    canonical_name="Example Security",
    country_code="FR",
)


def test_greenhouse_projection_updates_same_signal_and_opportunity() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)
    first_projection = _projection(
        _job(
            title="Senior SOC Analyst",
            content="<p>Security operations using Microsoft Sentinel.</p>",
        ),
        collected_at=NOW,
    )
    updated_at = NOW + timedelta(days=1)
    second_projection = _projection(
        _job(
            title="Lead SOC Analyst",
            updated_at="2026-08-05T11:00:00Z",
            content="<p>Security operations and Splunk Enterprise Security.</p>",
        ),
        collected_at=updated_at,
    )
    assert first_projection.signal.id == second_projection.signal.id
    assert first_projection.evidence.id == second_projection.evidence.id

    with factory() as session:
        first_ids = persist_commercial_projections(
            session,
            (first_projection,),
            now=NOW,
        )
        session.commit()
        first_signal = session.scalar(select(CommercialSignalRecord))
        first_evidence = session.scalar(select(EvidenceRecord))
        assert first_signal is not None and first_evidence is not None
        original_created_at = first_signal.created_at
        original_hash = first_evidence.content_hash_sha256

        second_ids = persist_commercial_projections(
            session,
            (second_projection,),
            now=updated_at,
        )
        session.commit()
        _assert_counts(session)
        assert second_ids == first_ids

        stored_signal = session.scalar(select(CommercialSignalRecord))
        stored_evidence = session.scalar(select(EvidenceRecord))
        assert stored_signal is not None and stored_evidence is not None
        assert stored_signal.title == "Lead SOC Analyst"
        assert stored_signal.matched_terms == [
            "soc analyst",
            "security operations",
            "splunk enterprise security",
        ]
        assert stored_signal.collected_at == updated_at
        assert stored_signal.expires_at == updated_at + timedelta(days=30)
        assert stored_signal.created_at == original_created_at
        assert stored_evidence.content_hash_sha256 != original_hash
        assert stored_evidence.collected_at == updated_at

        detail = get_opportunity_detail(session, first_ids[0])
        assert detail.opportunity.organization == "Example Security"
        assert detail.opportunity.country == "FR"
        assert detail.opportunity.evidence_count == 1
        assert detail.opportunity.data_quality == "partial"
        assert detail.opportunity.trigger.startswith("1 security-operations job posting")
        assert detail.evidence[0].source_id == "greenhouse-job-board"
        assert detail.evidence[0].source_url.endswith("/jobs/123")


def _projection(
    payload: dict[str, object],
    *,
    collected_at: datetime,
):
    mapped = map_greenhouse_job(
        BOARD,
        GreenhouseJob.model_validate(payload),
        collection_job_id=uuid4(),
        collected_at=collected_at,
        retention_until=collected_at + timedelta(days=365),
    )
    assert mapped is not None
    return mapped[1]


def _assert_counts(session: Session) -> None:
    assert session.scalar(select(func.count()).select_from(OrganizationRecord)) == 1
    assert session.scalar(select(func.count()).select_from(EvidenceRecord)) == 1
    assert session.scalar(select(func.count()).select_from(CommercialSignalRecord)) == 1
    assert session.scalar(select(func.count()).select_from(OpportunityRecord)) == 1


def _job(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": 123,
        "internal_job_id": 456,
        "title": "Senior SOC Analyst",
        "updated_at": "2026-08-04T11:00:00Z",
        "absolute_url": "https://job-boards.greenhouse.io/example/jobs/123",
        "location": {"name": "Paris or remote"},
        "language": "en",
        "content": "<p>Security operations using Microsoft Sentinel.</p>",
        "departments": [{"id": 1, "name": "Security"}],
        "offices": [{"id": 1, "name": "Paris"}],
        "metadata": None,
    }
    payload.update(changes)
    return payload

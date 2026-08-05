from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.modules.collection_orchestration.application import ted_adapter as adapter_module
from cip.modules.collection_orchestration.application.ted_adapter import TedSearchAdapter
from cip.modules.collection_orchestration.application.worker import (
    WorkerStatus,
    run_worker_once,
)
from cip.modules.collection_orchestration.domain.models import CollectionJob, SourceSchedule
from cip.modules.collection_orchestration.infrastructure.models import (
    CollectionCheckpointRecord,
)
from cip.modules.collection_orchestration.infrastructure.repository import enqueue_job
from cip.modules.data_governance.infrastructure.retention_loader import load_retention_policy
from cip.modules.opportunities.infrastructure.models import (
    CommercialSignalRecord,
    OpportunityRecord,
)
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.procurement_history.infrastructure.models import (
    ProcurementContractPartyRecord,
    ProcurementContractRecord,
    ProcurementProcedureRecord,
    ProcurementPublicationRecord,
)
from cip.modules.raw_observations.infrastructure.models import RawObservationRecord
from cip.modules.source_governance.infrastructure.persistence import sync_source_registry
from cip.modules.source_governance.infrastructure.registry import load_source_registry
from cip.modules.source_portfolio.application.service import sync_source_portfolio
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import session_scope

NOW = datetime(2026, 8, 5, 10, 0, tzinfo=UTC)


def test_ted_award_runs_to_contract_history_without_current_opportunity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = _factory()
    entries = load_source_registry(Path("policies/sources.example.yml"))
    ted_entry = next(entry for entry in entries if entry.policy.id == "ted-search")
    with session_scope(factory) as session:
        sync_source_registry(session, entries)
        sync_source_portfolio(
            session,
            load_source_portfolio(Path("policies/source_portfolio.yml")),
            now=NOW,
        )
        schedule = SourceSchedule(
            source_id="ted-search",
            adapter_id="ted-search-api",
            interval_seconds=900,
        )
        assert enqueue_job(
            session,
            CollectionJob.from_schedule(schedule, scheduled_for=NOW),
        )

    requests: list[httpx.Request] = []
    real_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            request=request,
            headers={"content-type": "application/json"},
            json={
                "notices": [
                    {
                        "publication-number": "700001-2026",
                        "notice-title": {
                            "eng": "Award of ISO 27001 audit, PAM and DFIR services"
                        },
                        "buyer-name": {"eng": ["European Runtime Buyer"]},
                        "buyer-country": ["FRA"],
                        "publication-date": "2026-08-05",
                        "deadline-receipt-tender-date-lot": None,
                        "classification-cpv": ["72000000"],
                        "notice-type": ["can-standard"],
                        "procedure-identifier": [
                            "7e9a7792-e8fd-4f3d-bdad-700001000001"
                        ],
                        "contract-identifier": ["CON-RUNTIME-700001"],
                        "contract-conclusion-date": ["2026-08-04"],
                        "winner-decision-date": ["2026-08-03"],
                        "winner-name": {"eng": ["Provider Runtime Europe SAS"]},
                        "winner-identifier": ["FR-987654321"],
                        "contract-title": {
                            "eng": "Audit, PAM and DFIR framework contract"
                        },
                        "tender-value": ["450000.00"],
                        "tender-value-cur": ["EUR"],
                    }
                ]
            },
        )

    def client_factory(*args: object, **kwargs: object) -> httpx.Client:
        kwargs.pop("transport", None)
        return real_client(
            *args,
            **kwargs,
            transport=httpx.MockTransport(handler),
        )

    monkeypatch.setattr(adapter_module.httpx, "Client", client_factory)
    adapter = TedSearchAdapter(ted_entry, timeout_seconds=5)
    outcome = run_worker_once(
        factory,
        worker_id="ted-award-test",
        adapters={(adapter.source_id, adapter.adapter_id): adapter},
        retention_policy=load_retention_policy(Path("policies/retention.yml")),
        clock=lambda: NOW + timedelta(seconds=1),
    )

    assert outcome.status is WorkerStatus.SUCCEEDED
    assert outcome.observations_written == 1
    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert requests[0].headers["accept"] == "application/json"
    assert b'"winner-name"' in requests[0].content
    with factory() as session:
        assert _count(session, RawObservationRecord) == 1
        assert _count(session, OrganizationRecord) == 1
        assert _count(session, ProcurementProcedureRecord) == 1
        assert _count(session, ProcurementPublicationRecord) == 1
        assert _count(session, ProcurementContractRecord) == 1
        assert _count(session, ProcurementContractPartyRecord) == 1
        assert _count(session, CommercialSignalRecord) == 0
        assert _count(session, OpportunityRecord) == 0
        contract = session.scalar(select(ProcurementContractRecord))
        assert contract is not None
        assert contract.currency == "EUR"
        assert contract.conclusion_date is not None
        party = session.scalar(select(ProcurementContractPartyRecord))
        assert party is not None
        assert party.published_name == "Provider Runtime Europe SAS"
        assert party.official_identifier == "FR-987654321"
        assert party.resolution_status == "unresolved"
        checkpoint = session.get(
            CollectionCheckpointRecord,
            ("ted-search", "ted-search-api"),
        )
        assert checkpoint is not None
        assert checkpoint.payload == {"latest_publication_number": "700001-2026"}


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

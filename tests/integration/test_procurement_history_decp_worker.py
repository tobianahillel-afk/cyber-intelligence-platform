from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.modules.collection_orchestration.application import decp_adapter as adapter_module
from cip.modules.collection_orchestration.application.decp_adapter import DecpAdapter
from cip.modules.collection_orchestration.application.worker import WorkerStatus, run_worker_once
from cip.modules.collection_orchestration.domain.models import CollectionJob, SourceSchedule
from cip.modules.collection_orchestration.infrastructure.models import CollectionCheckpointRecord
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


def test_decp_runs_to_contract_history_without_current_opportunity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = _factory()
    source_entry = load_source_registry(Path("policies/sources.decp.yml"))[0]
    portfolio = load_source_portfolio(Path("policies/source_portfolio.decp.yml"))
    with session_scope(factory) as session:
        sync_source_registry(session, (source_entry,))
        sync_source_portfolio(session, portfolio, now=NOW)
        schedule = SourceSchedule(
            source_id="decp",
            adapter_id="decp-explore-api",
            interval_seconds=86_400,
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
                "total_count": 1,
                "results": [
                    {
                        "id": "DECP-RUNTIME-001",
                        "nature": "Marché",
                        "objet": "Audit ISO 27001, PAM et réponse à incident",
                        "codecpv": "72000000",
                        "procedure": "Appel d'offres ouvert",
                        "acheteur_id": "11111111111111",
                        "acheteur_nom": "Métropole Runtime",
                        "dureemois": 12,
                        "datenotification": "2026-08-31",
                        "datepublicationdonnees": "2026-09-02",
                        "montant": 250000,
                        "titulaire_denominationsociale_1": "Provider Runtime SAS",
                        "titulaire_id_1": "22222222222222",
                        "titulaire_typeidentifiant_1": "SIRET",
                        "booleanmodification": False,
                    }
                ],
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
    adapter = DecpAdapter(source_entry, timeout_seconds=5)
    outcome = run_worker_once(
        factory,
        worker_id="decp-contract-test",
        adapters={(adapter.source_id, adapter.adapter_id): adapter},
        retention_policy=load_retention_policy(Path("policies/retention.yml")),
        clock=lambda: NOW + timedelta(seconds=1),
    )

    assert outcome.status is WorkerStatus.SUCCEEDED
    assert outcome.observations_written == 1
    assert len(requests) == 1
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
        assert contract.notification_date == date(2026, 8, 31)
        assert contract.end_date == date(2027, 8, 31)
        assert contract.renewal_date == date(2027, 8, 31)
        checkpoint = session.get(
            CollectionCheckpointRecord,
            ("decp", "decp-explore-api"),
        )
        assert checkpoint is not None
        assert checkpoint.payload["latest_revision_key"]
        assert checkpoint.payload["latest_publication_date"] == "2026-09-02"


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

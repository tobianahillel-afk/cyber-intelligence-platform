from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.adapters.sources.decp.mapper import map_decp_contract
from cip.adapters.sources.decp.schemas import DecpContract
from cip.modules.collection_orchestration.application.ports import (
    AdapterCollectionBatch,
    CommercialProjection,
)
from cip.modules.data_governance.infrastructure.retention_loader import load_retention_policy
from cip.modules.evidence.domain.entities import Evidence
from cip.modules.opportunities.domain.entities import CommercialSignal, SignalType
from cip.modules.opportunities.infrastructure.models import (
    CommercialSignalRecord,
    OpportunityRecord,
)
from cip.modules.procurement_history.infrastructure.models import (
    ProcurementContractRecord,
    ProcurementPublicationRecord,
)
from cip.modules.source_governance.domain.models import DataCategory
from cip.modules.source_governance.infrastructure.persistence import sync_source_registry
from cip.modules.source_governance.infrastructure.registry import load_source_registry
from cip.modules.source_portfolio.application.backfill_worker import (
    BackfillWorkerStatus,
    run_backfill_once,
)
from cip.modules.source_portfolio.application.service import request_backfill, sync_source_portfolio
from cip.modules.source_portfolio.infrastructure.models import SourceValueEventRecord
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import session_scope

NOW = datetime(2026, 8, 5, 10, 0, tzinfo=UTC)


class ProcurementBackfillAdapter:
    source_id = "decp"
    adapter_id = "decp-explore-api"
    data_category = DataCategory.PUBLIC_TENDER

    def collect(
        self,
        *,
        collection_job_id: UUID,
        checkpoint_payload: Mapping[str, object] | None,
        collected_at: datetime,
        retention_until: datetime,
    ) -> AdapterCollectionBatch:
        del checkpoint_payload
        mapped = map_decp_contract(
            DecpContract.model_validate(_record()),
            collection_job_id=collection_job_id,
            collected_at=collected_at,
            retention_until=retention_until,
        )
        assert mapped is not None
        evidence_id = uuid5(NAMESPACE_URL, "decp:forbidden-backfill-evidence")
        commercial = CommercialProjection(
            organization=mapped.buyer,
            evidence=Evidence(
                id=evidence_id,
                source_id="decp",
                source_record_key="historical-signal",
                source_url="https://data.economie.gouv.fr/",
                summary="Historical contract must not create a current opportunity.",
                confidence=0.9,
                collected_at=collected_at,
                content_hash_sha256="f" * 64,
                raw_storage_permitted=False,
                retention_until=retention_until,
            ),
            signal=CommercialSignal(
                id=uuid5(NAMESPACE_URL, "decp:forbidden-backfill-signal"),
                organization_id=mapped.buyer.id,
                evidence_id=evidence_id,
                signal_type=SignalType.PUBLIC_TENDER,
                title="Forbidden historical signal",
                summary="This projection must be ignored by the backfill worker.",
                confidence=0.9,
                matched_terms=("audit",),
                collected_at=collected_at,
                created_at=collected_at,
            ),
        )
        return AdapterCollectionBatch(
            observations=(mapped.observation,),
            checkpoint_payload={"completed": True},
            not_modified=False,
            commercial_projections=(commercial,),
            procurement_organizations=(mapped.buyer,),
            procurement_projections=(mapped.procurement,),
        )


def test_historical_backfill_persists_contract_but_ignores_current_signal() -> None:
    factory = _factory()
    with session_scope(factory) as session:
        sync_source_registry(
            session,
            load_source_registry(Path("policies/sources.decp.yml")),
        )
        sync_source_portfolio(
            session,
            load_source_portfolio(Path("policies/source_portfolio.decp.yml")),
            now=NOW,
        )
        partition_id = request_backfill(
            session,
            "decp",
            (("2026-01-01", "2026-01-31"),),
            actor="procurement-backfill-test",
            now=NOW,
        )[0]

    adapter = ProcurementBackfillAdapter()
    outcome = run_backfill_once(
        factory,
        worker_id="procurement-backfill-test",
        adapters={(adapter.source_id, adapter.adapter_id): adapter},
        retention_policy=load_retention_policy(Path("policies/retention.yml")),
        clock=lambda: NOW + timedelta(seconds=1),
    )

    assert outcome.status is BackfillWorkerStatus.SUCCEEDED
    assert outcome.partition_id == partition_id
    with factory() as session:
        assert _count(session, ProcurementPublicationRecord) == 1
        assert _count(session, ProcurementContractRecord) == 1
        assert _count(session, CommercialSignalRecord) == 0
        assert _count(session, OpportunityRecord) == 0
        value = session.scalar(select(SourceValueEventRecord))
        assert value is not None
        assert value.execution_mode == "historical_backfill"
        assert value.commercial_projections == 0


def _record() -> dict[str, object]:
    return {
        "id": "DECP-BACKFILL-001",
        "nature": "Marché",
        "objet": "Audit ISO 27001 et PAM historique",
        "codecpv": "72000000",
        "procedure": "Appel d'offres ouvert",
        "acheteur_id": "11111111111111",
        "acheteur_nom": "Métropole Historique",
        "dureemois": 12,
        "datenotification": "2025-01-31",
        "datepublicationdonnees": "2025-02-02",
        "montant": 250000,
        "titulaire_denominationsociale_1": "Provider Historique SAS",
        "titulaire_id_1": "22222222222222",
        "titulaire_typeidentifiant_1": "SIRET",
        "booleanmodification": False,
    }


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

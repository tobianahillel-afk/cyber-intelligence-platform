from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.procurement_history.domain.models import (
    ContractStatus,
    DateBasis,
    MoneyAmount,
    PartyResolutionStatus,
    ProcurementContractProjection,
    ProcurementHistoryProjection,
    ProcurementParty,
    ProcurementPartyRole,
    ProcurementProcedureStatus,
    ProcurementPublication,
    ProcurementPublicationKind,
)
from cip.modules.procurement_history.infrastructure.models import (
    ProcurementContractPartyRecord,
    ProcurementContractRecord,
    ProcurementProcedureRecord,
    ProcurementPublicationRecord,
    ProcurementServiceClassificationRecord,
)
from cip.modules.procurement_history.infrastructure.projections import (
    persist_procurement_projections,
)
from cip.modules.service_taxonomy.domain.models import (
    CyberServiceFamily,
    ServiceFamilyMatch,
)
from cip.shared.persistence.metadata import get_metadata

NOW = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)
BUYER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def test_open_notice_creates_history_without_contract_and_replay_is_idempotent() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        _add_buyer(session)
        notice = _history(ProcurementPublicationKind.NOTICE, "a" * 64)

        persist_procurement_projections(session, (notice,), now=NOW)
        persist_procurement_projections(
            session,
            (_history(ProcurementPublicationKind.NOTICE, "a" * 64),),
            now=NOW,
        )
        session.flush()

        assert _count(session, ProcurementProcedureRecord) == 1
        assert _count(session, ProcurementPublicationRecord) == 1
        assert _count(session, ProcurementContractRecord) == 0


def test_award_and_amendment_preserve_chronology_and_update_one_contract() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        _add_buyer(session)
        notice = _history(ProcurementPublicationKind.NOTICE, "a" * 64)
        award = _history(
            ProcurementPublicationKind.AWARD,
            "b" * 64,
            published_at=NOW + timedelta(days=1),
            contract=_contract(
                status=ContractStatus.AWARDED,
                end_date=date(2027, 8, 5),
                renewal_date=date(2027, 11, 5),
            ),
        )
        amendment = _history(
            ProcurementPublicationKind.AMENDMENT,
            "c" * 64,
            published_at=NOW + timedelta(days=2),
            contract=_contract(
                status=ContractStatus.ACTIVE,
                end_date=date(2028, 2, 5),
                renewal_date=date(2028, 5, 5),
            ),
        )

        persist_procurement_projections(session, (notice, award, amendment), now=NOW)
        session.flush()

        contract = session.scalar(select(ProcurementContractRecord))
        assert contract is not None
        assert _count(session, ProcurementProcedureRecord) == 1
        assert _count(session, ProcurementPublicationRecord) == 3
        assert _count(session, ProcurementContractRecord) == 1
        assert _count(session, ProcurementContractPartyRecord) == 1
        assert _count(session, ProcurementServiceClassificationRecord) == 2
        assert contract.status == ContractStatus.ACTIVE.value
        assert contract.end_date == date(2028, 2, 5)
        assert contract.end_date_basis == DateBasis.PUBLISHED.value
        assert contract.renewal_date_basis == DateBasis.ESTIMATED.value
        assert contract.amount_value == Decimal("250000.00")
        latest = session.get(ProcurementPublicationRecord, contract.latest_publication_id)
        assert latest is not None
        assert latest.kind == ProcurementPublicationKind.AMENDMENT.value


def test_older_publication_cannot_roll_back_current_contract_projection() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    with Session(engine) as session:
        _add_buyer(session)
        current = _history(
            ProcurementPublicationKind.AMENDMENT,
            "d" * 64,
            published_at=NOW + timedelta(days=3),
            contract=_contract(
                status=ContractStatus.ACTIVE,
                end_date=date(2028, 8, 5),
                renewal_date=date(2028, 11, 5),
            ),
        )
        older = _history(
            ProcurementPublicationKind.AWARD,
            "b" * 64,
            published_at=NOW + timedelta(days=1),
            contract=_contract(
                status=ContractStatus.AWARDED,
                end_date=date(2027, 8, 5),
                renewal_date=date(2027, 11, 5),
            ),
        )

        persist_procurement_projections(session, (current, older), now=NOW)
        session.flush()

        contract = session.scalar(select(ProcurementContractRecord))
        assert contract is not None
        assert contract.status == ContractStatus.ACTIVE.value
        assert contract.end_date == date(2028, 8, 5)
        assert _count(session, ProcurementPublicationRecord) == 2


def _history(
    kind: ProcurementPublicationKind,
    content_hash: str,
    *,
    published_at: datetime = NOW,
    contract: ProcurementContractProjection | None = None,
) -> ProcurementHistoryProjection:
    status = {
        ProcurementPublicationKind.NOTICE: ProcurementProcedureStatus.OPEN,
        ProcurementPublicationKind.AWARD: ProcurementProcedureStatus.AWARDED,
        ProcurementPublicationKind.AMENDMENT: ProcurementProcedureStatus.AWARDED,
    }[kind]
    publication = ProcurementPublication(
        id=uuid5(NAMESPACE_URL, f"publication:{content_hash}"),
        procedure_key="boamp:procedure:24-100001",
        source_id="boamp",
        source_record_key="24-100001",
        source_url="https://example.test/24-100001",
        kind=kind,
        procedure_status=status,
        buyer_organization_id=BUYER_ID,
        title="Audit, PAM and incident response framework agreement",
        content_hash_sha256=content_hash,
        collected_at=published_at,
        published_at=published_at,
        details={"lot": "1"},
    )
    return ProcurementHistoryProjection(publication=publication, contract=contract)


def _contract(
    *,
    status: ContractStatus,
    end_date: date,
    renewal_date: date,
) -> ProcurementContractProjection:
    return ProcurementContractProjection(
        contract_key="boamp:contract:24-100001:lot-1",
        procedure_key="boamp:procedure:24-100001",
        buyer_organization_id=BUYER_ID,
        title="Audit, PAM and incident response framework agreement",
        status=status,
        confidence=0.91,
        parties=(
            ProcurementParty(
                role=ProcurementPartyRole.AWARDEE,
                published_name="Provider SAS",
                resolution_status=PartyResolutionStatus.UNRESOLVED,
                confidence=0.7,
            ),
        ),
        service_families=(
            ServiceFamilyMatch(
                CyberServiceFamily.AUDIT_RISK_ASSESSMENT,
                ("audit",),
                0.8,
            ),
            ServiceFamilyMatch(
                CyberServiceFamily.IAM_IGA_PAM_ZERO_TRUST,
                ("pam",),
                0.8,
            ),
        ),
        amount=MoneyAmount(value=Decimal("250000.00"), currency="EUR"),
        award_date=date(2026, 8, 5),
        end_date=end_date,
        end_date_basis=DateBasis.PUBLISHED,
        renewal_date=renewal_date,
        renewal_date_basis=DateBasis.ESTIMATED,
    )


def _add_buyer(session: Session) -> None:
    session.add(
        OrganizationRecord(
            id=BUYER_ID,
            canonical_name="Public Buyer",
            legal_name="Public Buyer",
            country_code="FR",
            website_url=None,
            registration_ids=[],
            created_at=NOW,
            updated_at=NOW,
        )
    )
    session.flush()


def _count(session: Session, record_type: type[object]) -> int:
    return int(session.scalar(select(func.count()).select_from(record_type)) or 0)

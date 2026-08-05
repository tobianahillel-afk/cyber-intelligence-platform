from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from cip.modules.procurement_history.domain.models import (
    AmountType,
    ContractStatus,
    DateBasis,
    MoneyAmount,
    PartyResolutionStatus,
    ProcurementContractProjection,
    ProcurementParty,
    ProcurementPartyRole,
    ProcurementPublication,
    ProcurementPublicationKind,
    ProcurementProcedureStatus,
)
from cip.modules.service_taxonomy.domain.models import CyberServiceFamily, ServiceFamilyMatch

NOW = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)
BUYER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def test_money_requires_valid_currency_and_range_bounds() -> None:
    amount = MoneyAmount(
        value=Decimal("100.00"),
        upper_value=Decimal("125.00"),
        currency="eur",
        amount_type=AmountType.RANGE,
    )

    assert amount.currency == "EUR"
    with pytest.raises(ValueError, match="currency"):
        MoneyAmount(value=Decimal("1"), currency="EU")
    with pytest.raises(ValueError, match="upper_value"):
        MoneyAmount(
            value=Decimal("100"),
            upper_value=Decimal("99"),
            currency="EUR",
            amount_type=AmountType.RANGE,
        )


def test_confirmed_party_requires_canonical_organization() -> None:
    with pytest.raises(ValueError, match="organization_id"):
        ProcurementParty(
            role=ProcurementPartyRole.AWARDEE,
            published_name="Provider SAS",
            resolution_status=PartyResolutionStatus.CONFIRMED,
            confidence=0.99,
        )


def test_publication_revision_key_changes_only_with_revision_content() -> None:
    publication = _publication()
    replay = _publication(publication_id=uuid4())
    changed = _publication(content_hash="b" * 64)

    assert replay.revision_key == publication.revision_key
    assert changed.revision_key != publication.revision_key


def test_contract_distinguishes_estimated_and_published_dates() -> None:
    contract = _contract(
        end_date=date(2027, 8, 5),
        end_date_basis=DateBasis.PUBLISHED,
        renewal_date=date(2027, 11, 5),
        renewal_date_basis=DateBasis.ESTIMATED,
    )

    assert contract.end_date_basis is DateBasis.PUBLISHED
    assert contract.renewal_date_basis is DateBasis.ESTIMATED
    with pytest.raises(ValueError, match="basis"):
        _contract(end_date=date(2027, 8, 5), end_date_basis=DateBasis.UNKNOWN)


def test_contract_deduplicates_parties_and_service_families() -> None:
    party = ProcurementParty(
        role=ProcurementPartyRole.AWARDEE,
        published_name="Provider SAS",
        organization_id=uuid4(),
        resolution_status=PartyResolutionStatus.CONFIRMED,
        confidence=0.98,
    )
    older = ServiceFamilyMatch(
        CyberServiceFamily.GRC_COMPLIANCE,
        ("iso 27001",),
        0.78,
    )
    newer = ServiceFamilyMatch(
        CyberServiceFamily.GRC_COMPLIANCE,
        ("grc", "iso 27001"),
        0.84,
    )

    contract = _contract(parties=(party, party), service_families=(older, newer))

    assert contract.parties == (party,)
    assert contract.service_families == (newer,)


def _publication(
    *,
    publication_id: UUID | None = None,
    content_hash: str = "a" * 64,
) -> ProcurementPublication:
    return ProcurementPublication(
        id=publication_id or uuid4(),
        procedure_key="boamp:procedure:24-100001",
        source_id="boamp",
        source_record_key="24-100001",
        source_url="https://example.test/24-100001",
        kind=ProcurementPublicationKind.AWARD,
        procedure_status=ProcurementProcedureStatus.AWARDED,
        buyer_organization_id=BUYER_ID,
        title="Cybersecurity framework agreement",
        content_hash_sha256=content_hash,
        collected_at=NOW,
        published_at=NOW,
        details={"lot": "1"},
    )


def _contract(
    *,
    parties: tuple[ProcurementParty, ...] = (),
    service_families: tuple[ServiceFamilyMatch, ...] = (),
    end_date: date | None = None,
    end_date_basis: DateBasis = DateBasis.UNKNOWN,
    renewal_date: date | None = None,
    renewal_date_basis: DateBasis = DateBasis.UNKNOWN,
) -> ProcurementContractProjection:
    return ProcurementContractProjection(
        contract_key="boamp:contract:24-100001:lot-1",
        procedure_key="boamp:procedure:24-100001",
        buyer_organization_id=BUYER_ID,
        title="Cybersecurity framework agreement",
        status=ContractStatus.AWARDED,
        publication=_publication(),
        confidence=0.92,
        parties=parties,
        service_families=service_families,
        end_date=end_date,
        end_date_basis=end_date_basis,
        renewal_date=renewal_date,
        renewal_date_basis=renewal_date_basis,
    )

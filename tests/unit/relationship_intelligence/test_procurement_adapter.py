from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from cip.modules.procurement_history.domain.models import (
    ContractStatus,
    DateBasis,
    PartyResolutionStatus,
    ProcurementContractProjection,
    ProcurementHistoryProjection,
    ProcurementParty,
    ProcurementPartyRole,
    ProcurementProcedureStatus,
    ProcurementPublication,
    ProcurementPublicationKind,
)
from cip.modules.relationship_intelligence.application.procurement_adapter import (
    relationship_bundle_from_procurement,
)
from cip.modules.relationship_intelligence.domain.models import (
    RelationshipClaimType,
    RelationshipEvidenceClass,
    RelationshipOrganizationLinkStatus,
    RelationshipRole,
)
from cip.modules.service_taxonomy.domain.models import CyberServiceFamily, ServiceFamilyMatch

NOW = datetime(2026, 8, 7, 19, 30, tzinfo=UTC)
BUYER_ID = uuid4()
PROVIDER_ID = uuid4()


def test_confirmed_awardee_becomes_contract_backed_provider_evidence() -> None:
    bundle = relationship_bundle_from_procurement(_projection(), observed_at=NOW)

    assert len(bundle.evidence) == 1
    evidence = bundle.evidence[0]
    assert evidence.role is RelationshipRole.PROVIDER
    assert evidence.evidence_class is RelationshipEvidenceClass.CONTRACTED
    assert evidence.source_organization_id == PROVIDER_ID
    assert evidence.target_organization_id == BUYER_ID
    assert evidence.source_link_status is RelationshipOrganizationLinkStatus.EXACT
    assert evidence.target_link_status is RelationshipOrganizationLinkStatus.EXACT
    assert evidence.contract_reference == "contract-42"
    assert evidence.active is True
    assert {context.context_type for context in bundle.contexts} == {"contract", "service"}


def test_completed_contract_is_historical_not_current_by_construction() -> None:
    projection = _projection(status=ContractStatus.COMPLETED)

    bundle = relationship_bundle_from_procurement(projection, observed_at=NOW)

    evidence = bundle.evidence[0]
    assert evidence.historical_only is True
    assert evidence.claim_type is RelationshipClaimType.ASSERTION


def test_cancelled_contract_emits_visible_retraction_revision() -> None:
    projection = _projection(status=ContractStatus.CANCELLED)

    bundle = relationship_bundle_from_procurement(projection, observed_at=NOW)

    evidence = bundle.evidence[0]
    assert evidence.claim_type is RelationshipClaimType.RETRACTION
    assert evidence.historical_only is True
    assert evidence.active is True


def test_candidate_awardee_stays_candidate_identity() -> None:
    projection = _projection(
        party=ProcurementParty(
            role=ProcurementPartyRole.AWARDEE,
            published_name="Provider Candidate",
            resolution_status=PartyResolutionStatus.CANDIDATE,
            confidence=0.6,
        )
    )

    evidence = relationship_bundle_from_procurement(projection, observed_at=NOW).evidence[0]

    assert evidence.source_organization_id is None
    assert evidence.source_link_status is RelationshipOrganizationLinkStatus.CANDIDATE


def test_subcontractor_keeps_directed_subcontractor_role() -> None:
    projection = _projection(
        party=ProcurementParty(
            role=ProcurementPartyRole.SUBCONTRACTOR,
            published_name="Subcontractor A",
            resolution_status=PartyResolutionStatus.CONFIRMED,
            confidence=0.8,
            organization_id=PROVIDER_ID,
        )
    )

    evidence = relationship_bundle_from_procurement(projection, observed_at=NOW).evidence[0]

    assert evidence.role is RelationshipRole.SUBCONTRACTOR
    assert evidence.target_organization_id == BUYER_ID


def test_non_contract_publication_produces_no_relationship() -> None:
    projection = ProcurementHistoryProjection(publication=_publication(), contract=None)

    bundle = relationship_bundle_from_procurement(projection, observed_at=NOW)

    assert bundle.evidence == ()
    assert bundle.contexts == ()


def _projection(
    *,
    status: ContractStatus = ContractStatus.ACTIVE,
    party: ProcurementParty | None = None,
) -> ProcurementHistoryProjection:
    selected_party = party or ProcurementParty(
        role=ProcurementPartyRole.AWARDEE,
        published_name="Provider A",
        resolution_status=PartyResolutionStatus.CONFIRMED,
        confidence=0.95,
        organization_id=PROVIDER_ID,
    )
    contract = ProcurementContractProjection(
        contract_key="contract-42",
        procedure_key="procedure-42",
        buyer_organization_id=BUYER_ID,
        title="Managed detection and response services",
        status=status,
        confidence=0.9,
        parties=(selected_party,),
        service_families=(
            ServiceFamilyMatch(
                family=CyberServiceFamily.SOC_SIEM_MDR_XDR_SOAR,
                matched_terms=("managed detection",),
                confidence=0.9,
            ),
        ),
        start_date=date(2026, 1, 1),
        start_date_basis=DateBasis.PUBLISHED,
        end_date=date(2026, 12, 31),
        end_date_basis=DateBasis.PUBLISHED,
        renewal_date=date(2027, 1, 31),
        renewal_date_basis=DateBasis.PUBLISHED,
    )
    return ProcurementHistoryProjection(publication=_publication(), contract=contract)


def _publication() -> ProcurementPublication:
    return ProcurementPublication(
        procedure_key="procedure-42",
        source_id="decp",
        source_record_key="award-42",
        source_url="https://example.org/contracts/42",
        kind=ProcurementPublicationKind.AWARD,
        procedure_status=ProcurementProcedureStatus.AWARDED,
        buyer_organization_id=BUYER_ID,
        title="Managed detection and response services",
        content_hash_sha256="a" * 64,
        collected_at=NOW,
        published_at=replace_time(NOW),
    )


def replace_time(value: datetime) -> datetime:
    return value.replace(hour=18)

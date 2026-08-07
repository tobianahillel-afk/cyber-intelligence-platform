from __future__ import annotations

from datetime import UTC, date, datetime

from cip.modules.procurement_history.domain.models import (
    ContractStatus,
    PartyResolutionStatus,
    ProcurementHistoryProjection,
    ProcurementParty,
    ProcurementPartyRole,
    ProcurementPublicationKind,
)
from cip.modules.relationship_intelligence.application.bundles import (
    RelationshipProjectionBundle,
)
from cip.modules.relationship_intelligence.domain.models import (
    RelationshipClaimType,
    RelationshipContext,
    RelationshipEvidenceClass,
    RelationshipEvidenceSnapshot,
    RelationshipOrganizationLinkStatus,
    RelationshipRole,
    RelationshipSourceKind,
)
from cip.shared.kernel.time import require_aware_utc


def relationship_bundle_from_procurement(
    projection: ProcurementHistoryProjection,
    *,
    observed_at: datetime,
) -> RelationshipProjectionBundle:
    current_observation = require_aware_utc(observed_at, field_name="observed_at")
    contract = projection.contract
    if contract is None:
        return RelationshipProjectionBundle(evidence=(), contexts=())
    awardees = tuple(
        party
        for party in contract.parties
        if party.role
        in {
            ProcurementPartyRole.AWARDEE,
            ProcurementPartyRole.CONSORTIUM_MEMBER,
            ProcurementPartyRole.SUBCONTRACTOR,
        }
    )
    evidence = tuple(
        _relationship_evidence(
            projection,
            party,
            observed_at=current_observation,
        )
        for party in awardees
    )
    contexts = _relationship_contexts(projection, evidence)
    return RelationshipProjectionBundle(evidence=evidence, contexts=contexts)


def _relationship_evidence(
    projection: ProcurementHistoryProjection,
    party: ProcurementParty,
    *,
    observed_at: datetime,
) -> RelationshipEvidenceSnapshot:
    contract = projection.contract
    if contract is None:
        raise ValueError("procurement relationship evidence requires a contract")
    publication = projection.publication
    relationship_key = _relationship_key(contract.contract_key, party)
    claim_type = (
        RelationshipClaimType.RETRACTION
        if contract.status is ContractStatus.CANCELLED
        or publication.kind is ProcurementPublicationKind.CANCELLATION
        else RelationshipClaimType.ASSERTION
    )
    historical_only = contract.status in {ContractStatus.COMPLETED, ContractStatus.CANCELLED}
    return RelationshipEvidenceSnapshot(
        source_id=publication.source_id,
        source_kind=RelationshipSourceKind.PROCUREMENT,
        source_record_key=f"{publication.source_record_key}:{party.identity_key}",
        source_url=publication.source_url,
        relationship_key=relationship_key,
        claim_type=claim_type,
        role=_relationship_role(party.role),
        evidence_class=RelationshipEvidenceClass.CONTRACTED,
        title=contract.title,
        excerpt=_contract_excerpt(contract.title, party.published_name),
        claimed_source_organization_name=party.published_name,
        claimed_target_organization_name=None,
        source_organization_id=party.organization_id,
        target_organization_id=contract.buyer_organization_id,
        source_link_status=_party_link_status(party),
        target_link_status=RelationshipOrganizationLinkStatus.EXACT,
        published_at=publication.published_at or publication.collected_at,
        modified_at=publication.collected_at,
        observed_at=observed_at,
        valid_from=_date_time(contract.start_date),
        valid_until=_date_time(contract.end_date),
        contract_reference=contract.contract_key,
        renewal_at=_date_time(contract.renewal_date),
        independence_key=publication.source_id,
        confidence=min(contract.confidence, party.confidence),
        active=True,
        historical_only=historical_only,
        supersedes_record_key=None,
    )


def _relationship_contexts(
    projection: ProcurementHistoryProjection,
    evidence: tuple[RelationshipEvidenceSnapshot, ...],
) -> tuple[RelationshipContext, ...]:
    contract = projection.contract
    if contract is None:
        return ()
    contexts: list[RelationshipContext] = []
    for snapshot in evidence:
        contexts.append(
            RelationshipContext(
                relationship_key=snapshot.relationship_key,
                context_type="contract",
                value=contract.contract_key,
                reference=projection.publication.source_url,
                confidence=contract.confidence,
            )
        )
        contexts.extend(
            RelationshipContext(
                relationship_key=snapshot.relationship_key,
                context_type="service",
                value=match.family.value,
                reference=projection.publication.source_url,
                confidence=match.confidence,
            )
            for match in contract.service_families
        )
    return tuple(contexts)


def _party_link_status(party: ProcurementParty) -> RelationshipOrganizationLinkStatus:
    if party.resolution_status is PartyResolutionStatus.CONFIRMED:
        return RelationshipOrganizationLinkStatus.EXACT
    if party.resolution_status is PartyResolutionStatus.CANDIDATE:
        return RelationshipOrganizationLinkStatus.CANDIDATE
    return RelationshipOrganizationLinkStatus.UNRESOLVED


def _relationship_role(role: ProcurementPartyRole) -> RelationshipRole:
    if role is ProcurementPartyRole.SUBCONTRACTOR:
        return RelationshipRole.SUBCONTRACTOR
    return RelationshipRole.PROVIDER


def _relationship_key(contract_key: str, party: ProcurementParty) -> str:
    return f"procurement:{contract_key}:{party.identity_key}:{_relationship_role(party.role).value}"


def _date_time(value: date | None) -> datetime | None:
    return datetime.combine(value, datetime.min.time(), tzinfo=UTC) if value else None


def _contract_excerpt(title: str, party_name: str) -> str:
    text = f"Published contract: {party_name} — {title}"
    return text[:500]

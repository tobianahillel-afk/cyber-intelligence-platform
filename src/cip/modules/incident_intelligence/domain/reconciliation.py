from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from cip.modules.incident_intelligence.domain.models import (
    IncidentClaimSnapshot,
    IncidentClaimType,
    IncidentStatus,
    IncidentType,
    OrganizationLinkStatus,
    ReconciledIncident,
)

_TYPE_PRIORITY = {
    IncidentType.UNKNOWN: 0,
    IncidentType.MALWARE: 1,
    IncidentType.SERVICE_DISRUPTION: 2,
    IncidentType.UNAUTHORIZED_ACCESS: 3,
    IncidentType.BUSINESS_EMAIL_COMPROMISE: 4,
    IncidentType.DATA_BREACH: 5,
    IncidentType.EXTORTION: 6,
    IncidentType.RANSOMWARE: 7,
    IncidentType.SUPPLY_CHAIN: 8,
}
_LINK_PRIORITY = {
    OrganizationLinkStatus.REJECTED: 0,
    OrganizationLinkStatus.UNRESOLVED: 1,
    OrganizationLinkStatus.CANDIDATE: 2,
    OrganizationLinkStatus.REVIEW_REQUIRED: 3,
    OrganizationLinkStatus.EXACT: 4,
}


def reconcile_incident_claims(
    claims: Iterable[IncidentClaimSnapshot],
) -> tuple[ReconciledIncident, ...]:
    current_claims = _latest_claim_revisions(tuple(claims))
    grouped: dict[str, list[IncidentClaimSnapshot]] = {}
    for claim in current_claims:
        grouped.setdefault(claim.incident_key, []).append(claim)
    return tuple(
        _reconcile_incident(tuple(grouped[key]))
        for key in sorted(grouped)
    )


def _latest_claim_revisions(
    claims: tuple[IncidentClaimSnapshot, ...],
) -> tuple[IncidentClaimSnapshot, ...]:
    latest: dict[tuple[str, str], IncidentClaimSnapshot] = {}
    for claim in claims:
        key = (claim.source_id, claim.source_record_key)
        current = latest.get(key)
        if current is None or claim.modified_at > current.modified_at:
            latest[key] = claim
    return tuple(latest.values())


def _reconcile_incident(
    claims: tuple[IncidentClaimSnapshot, ...],
) -> ReconciledIncident:
    if not claims:
        raise ValueError("cannot reconcile an empty incident claim group")
    ordered = tuple(
        sorted(
            claims,
            key=lambda item: (
                not item.is_official_confirmation,
                -item.confidence,
                -item.modified_at.timestamp(),
            ),
        )
    )
    positive = tuple(claim for claim in claims if claim.active and claim.is_positive_claim)
    official = tuple(claim for claim in positive if claim.is_official_confirmation)
    denials = tuple(
        claim
        for claim in claims
        if claim.active and claim.claim_type is IncidentClaimType.DENIAL
    )
    retractions = tuple(
        claim
        for claim in claims
        if claim.active and claim.claim_type is IncidentClaimType.RETRACTION
    )
    organization_id, link_status = _organization_link(claims)
    return ReconciledIncident(
        incident_key=claims[0].incident_key,
        incident_type=max(
            (claim.incident_type for claim in claims),
            key=_TYPE_PRIORITY.__getitem__,
        ),
        title=ordered[0].title,
        summary=ordered[0].summary,
        status=_incident_status(
            positive,
            official,
            denials,
            retractions,
        ),
        organization_id=organization_id,
        organization_link_status=link_status,
        claimed_organization_names=tuple(
            sorted(
                {
                    claim.claimed_organization_name
                    for claim in claims
                    if claim.claimed_organization_name is not None
                }
            )
        ),
        occurrence_start_at=_minimum_time(
            claim.occurrence_start_at for claim in claims
        ),
        occurrence_end_at=_maximum_time(
            claim.occurrence_end_at for claim in claims
        ),
        discovered_at=_minimum_time(
            claim.discovered_at for claim in claims
        ),
        first_published_at=min(claim.published_at for claim in claims),
        confirmed_at=_minimum_time(
            claim.confirmed_at for claim in official
        ),
        last_updated_at=max(claim.modified_at for claim in claims),
        claim_count=len(claims),
        independent_source_count=len(
            {
                claim.independence_key
                for claim in positive
                if claim.independence_key is not None
            }
        ),
        officially_confirmed=bool(official),
        has_denial=bool(denials),
        has_retraction=bool(retractions),
        historical_only=all(claim.historical_only for claim in claims),
    )


def _incident_status(
    positive: tuple[IncidentClaimSnapshot, ...],
    official: tuple[IncidentClaimSnapshot, ...],
    denials: tuple[IncidentClaimSnapshot, ...],
    retractions: tuple[IncidentClaimSnapshot, ...],
) -> IncidentStatus:
    if official:
        return IncidentStatus.CONFIRMED
    if positive:
        if all(
            claim.claim_type is IncidentClaimType.ATTACKER_ALLEGATION
            for claim in positive
        ):
            return IncidentStatus.ALLEGED
        return IncidentStatus.REPORTED
    if denials:
        return IncidentStatus.DENIED
    if retractions:
        return IncidentStatus.RETRACTED
    return IncidentStatus.UNDER_REVIEW


def _organization_link(
    claims: tuple[IncidentClaimSnapshot, ...],
) -> tuple[UUID | None, OrganizationLinkStatus]:
    exact_ids = {
        claim.organization_id
        for claim in claims
        if claim.active
        and claim.organization_link_status is OrganizationLinkStatus.EXACT
        and claim.organization_id is not None
    }
    if len(exact_ids) > 1:
        return None, OrganizationLinkStatus.REVIEW_REQUIRED
    if len(exact_ids) == 1:
        return next(iter(exact_ids)), OrganizationLinkStatus.EXACT
    strongest = max(
        (claim.organization_link_status for claim in claims),
        key=_LINK_PRIORITY.__getitem__,
    )
    return None, strongest


def _minimum_time(values: Iterable[datetime | None]) -> datetime | None:
    present = tuple(value for value in values if value is not None)
    return min(present) if present else None


def _maximum_time(values: Iterable[datetime | None]) -> datetime | None:
    present = tuple(value for value in values if value is not None)
    return max(present) if present else None

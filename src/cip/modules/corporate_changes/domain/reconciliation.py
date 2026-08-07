from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from cip.modules.corporate_changes.domain.models import (
    ChangeClaimSnapshot,
    ChangeClaimType,
    ChangeEventStatus,
    OrganizationLinkStatus,
    ReconciledChangeEvent,
)
from cip.shared.kernel.time import require_aware_utc

_LINK_PRIORITY = {
    OrganizationLinkStatus.REJECTED: 0,
    OrganizationLinkStatus.UNRESOLVED: 1,
    OrganizationLinkStatus.CANDIDATE: 2,
    OrganizationLinkStatus.REVIEW_REQUIRED: 3,
    OrganizationLinkStatus.EXACT: 4,
}
_POSITIVE_TYPES = {
    ChangeClaimType.CONFIRMATION,
    ChangeClaimType.REPORT,
    ChangeClaimType.SPECULATION,
}


def reconcile_change_claims(
    claims: Iterable[ChangeClaimSnapshot],
    *,
    now: datetime,
) -> tuple[ReconciledChangeEvent, ...]:
    current = require_aware_utc(now, field_name="now")
    latest_claims = _latest_claim_revisions(tuple(claims))
    grouped: dict[str, list[ChangeClaimSnapshot]] = {}
    for claim in latest_claims:
        grouped.setdefault(claim.event_key, []).append(claim)
    return tuple(
        _reconcile_event(tuple(grouped[key]), now=current)
        for key in sorted(grouped)
    )


def _latest_claim_revisions(
    claims: tuple[ChangeClaimSnapshot, ...],
) -> tuple[ChangeClaimSnapshot, ...]:
    latest: dict[tuple[str, str], ChangeClaimSnapshot] = {}
    for claim in claims:
        key = (claim.source_id, claim.source_record_key)
        existing = latest.get(key)
        if existing is None or claim.modified_at > existing.modified_at:
            latest[key] = claim
    superseded = {
        (claim.source_id, claim.supersedes_record_key)
        for claim in latest.values()
        if claim.supersedes_record_key is not None
    }
    return tuple(
        claim
        for key, claim in latest.items()
        if key not in superseded
    )


def _reconcile_event(
    claims: tuple[ChangeClaimSnapshot, ...],
    *,
    now: datetime,
) -> ReconciledChangeEvent:
    if not claims:
        raise ValueError("cannot reconcile an empty change-claim group")
    active = tuple(claim for claim in claims if claim.active)
    positive = tuple(claim for claim in active if claim.claim_type in _POSITIVE_TYPES)
    official = tuple(claim for claim in positive if claim.is_official_confirmation)
    disputes = _claims_of_type(active, ChangeClaimType.DISPUTE)
    corrections = _claims_of_type(active, ChangeClaimType.CORRECTION)
    retractions = _claims_of_type(active, ChangeClaimType.RETRACTION)
    organization_id, link_status = _organization_link(claims)
    preferred = _preferred_claim(claims)
    return ReconciledChangeEvent(
        event_key=claims[0].event_key,
        event_type=preferred.event_type,
        title=preferred.title,
        excerpt=preferred.excerpt,
        status=_event_status(
            positive,
            official,
            disputes,
            corrections,
            retractions,
            now=now,
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
        event_at=_minimum_time(claim.event_at for claim in claims),
        first_published_at=min(claim.published_at for claim in claims),
        last_updated_at=max(claim.modified_at for claim in claims),
        claim_count=len(claims),
        independent_source_count=len(
            {claim.corroboration_key for claim in positive}
        ),
        officially_confirmed=bool(official),
        has_dispute=bool(disputes),
        has_correction=bool(corrections),
        has_retraction=bool(retractions),
        historical_only=bool(claims) and all(claim.historical_only for claim in claims),
    )


def _event_status(
    positive: tuple[ChangeClaimSnapshot, ...],
    official: tuple[ChangeClaimSnapshot, ...],
    disputes: tuple[ChangeClaimSnapshot, ...],
    corrections: tuple[ChangeClaimSnapshot, ...],
    retractions: tuple[ChangeClaimSnapshot, ...],
    *,
    now: datetime,
) -> ChangeEventStatus:
    fresh_positive = tuple(claim for claim in positive if not claim.is_stale_at(now))
    if official and any(not claim.is_stale_at(now) for claim in official):
        return ChangeEventStatus.CONFIRMED
    if disputes and fresh_positive:
        return ChangeEventStatus.DISPUTED
    if fresh_positive:
        if all(claim.claim_type is ChangeClaimType.SPECULATION for claim in fresh_positive):
            return ChangeEventStatus.SPECULATIVE
        return ChangeEventStatus.REPORTED
    if positive:
        return ChangeEventStatus.STALE
    if retractions:
        return ChangeEventStatus.RETRACTED
    if corrections:
        return ChangeEventStatus.CORRECTED
    if disputes:
        return ChangeEventStatus.DISPUTED
    return ChangeEventStatus.UNDER_REVIEW


def _preferred_claim(claims: tuple[ChangeClaimSnapshot, ...]) -> ChangeClaimSnapshot:
    return min(
        claims,
        key=lambda item: (
            not item.is_official_confirmation,
            item.claim_type is ChangeClaimType.SPECULATION,
            -item.confidence,
            -item.modified_at.timestamp(),
        ),
    )


def _claims_of_type(
    claims: tuple[ChangeClaimSnapshot, ...],
    claim_type: ChangeClaimType,
) -> tuple[ChangeClaimSnapshot, ...]:
    return tuple(claim for claim in claims if claim.claim_type is claim_type)


def _organization_link(
    claims: tuple[ChangeClaimSnapshot, ...],
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

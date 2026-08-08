from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from cip.modules.relationship_intelligence.domain.models import (
    ReconciledRelationship,
    RelationshipClaimType,
    RelationshipEvidenceClass,
    RelationshipEvidenceSnapshot,
    RelationshipOrganizationLinkStatus,
    RelationshipStatus,
    role_can_be_contract_backed_incumbent,
)
from cip.shared.kernel.time import require_aware_utc

_LINK_PRIORITY = {
    RelationshipOrganizationLinkStatus.REJECTED: 0,
    RelationshipOrganizationLinkStatus.UNRESOLVED: 1,
    RelationshipOrganizationLinkStatus.CANDIDATE: 2,
    RelationshipOrganizationLinkStatus.REVIEW_REQUIRED: 3,
    RelationshipOrganizationLinkStatus.EXACT: 4,
}
_EVIDENCE_PRIORITY = {
    RelationshipEvidenceClass.HISTORICAL: 0,
    RelationshipEvidenceClass.INFERRED: 1,
    RelationshipEvidenceClass.CLAIMED: 2,
    RelationshipEvidenceClass.OBSERVED: 3,
    RelationshipEvidenceClass.CONTRACTED: 4,
}


def reconcile_relationship_evidence(
    evidence: Iterable[RelationshipEvidenceSnapshot],
    *,
    now: datetime,
) -> tuple[ReconciledRelationship, ...]:
    current = require_aware_utc(now, field_name="now")
    latest = _latest_revisions(tuple(evidence))
    grouped: dict[str, list[RelationshipEvidenceSnapshot]] = {}
    for snapshot in latest:
        grouped.setdefault(snapshot.relationship_key, []).append(snapshot)
    return tuple(
        _reconcile_relationship(tuple(grouped[key]), now=current)
        for key in sorted(grouped)
    )


def _latest_revisions(
    evidence: tuple[RelationshipEvidenceSnapshot, ...],
) -> tuple[RelationshipEvidenceSnapshot, ...]:
    latest: dict[tuple[str, str], RelationshipEvidenceSnapshot] = {}
    for snapshot in evidence:
        key = (snapshot.source_id, snapshot.source_record_key)
        existing = latest.get(key)
        if existing is None or snapshot.modified_at > existing.modified_at:
            latest[key] = snapshot
    superseded = {
        (snapshot.source_id, snapshot.supersedes_record_key)
        for snapshot in latest.values()
        if snapshot.supersedes_record_key is not None
    }
    return tuple(snapshot for key, snapshot in latest.items() if key not in superseded)


def _reconcile_relationship(
    evidence: tuple[RelationshipEvidenceSnapshot, ...],
    *,
    now: datetime,
) -> ReconciledRelationship:
    if not evidence:
        raise ValueError("cannot reconcile an empty relationship evidence group")
    active = tuple(snapshot for snapshot in evidence if snapshot.active)
    assertions = tuple(
        snapshot
        for snapshot in active
        if snapshot.claim_type is RelationshipClaimType.ASSERTION
    )
    disputes = _of_type(active, RelationshipClaimType.DISPUTE)
    corrections = _of_type(active, RelationshipClaimType.CORRECTION)
    retractions = _of_type(active, RelationshipClaimType.RETRACTION)
    roles = {snapshot.role for snapshot in assertions}
    role_conflict = len(roles) > 1
    preferred = _preferred_snapshot(evidence, now=now)
    source_id, source_status = _organization_link(evidence, source=True)
    target_id, target_status = _organization_link(evidence, source=False)
    if source_id is not None and source_id == target_id:
        source_id = None
        target_id = None
        source_status = RelationshipOrganizationLinkStatus.REVIEW_REQUIRED
        target_status = RelationshipOrganizationLinkStatus.REVIEW_REQUIRED
    contract_evidence = tuple(
        snapshot for snapshot in assertions if snapshot.is_contract_evidence_at(now)
    )
    status = _relationship_status(
        assertions,
        disputes,
        corrections,
        retractions,
        role_conflict=role_conflict,
        now=now,
    )
    renewals = tuple(
        snapshot.renewal_at
        for snapshot in contract_evidence
        if snapshot.renewal_at is not None and snapshot.renewal_at >= now
    )
    confidence = max(
        (snapshot.confidence for snapshot in assertions),
        default=preferred.confidence,
    )
    return ReconciledRelationship(
        relationship_key=evidence[0].relationship_key,
        role=preferred.role,
        status=status,
        source_organization_id=source_id,
        target_organization_id=target_id,
        source_link_status=source_status,
        target_link_status=target_status,
        claimed_source_organization_names=_claimed_names(evidence, source=True),
        claimed_target_organization_names=_claimed_names(evidence, source=False),
        valid_from=_minimum_time(snapshot.valid_from for snapshot in assertions),
        valid_until=_maximum_time(snapshot.valid_until for snapshot in assertions),
        first_published_at=min(snapshot.published_at for snapshot in evidence),
        last_updated_at=max(snapshot.modified_at for snapshot in evidence),
        last_observed_at=max(snapshot.observed_at for snapshot in evidence),
        evidence_count=len(evidence),
        independent_source_count=len(
            {snapshot.independence_key or snapshot.source_id for snapshot in assertions}
        ),
        strongest_evidence_class=max(
            (snapshot.evidence_class for snapshot in assertions),
            key=_EVIDENCE_PRIORITY.__getitem__,
            default=preferred.evidence_class,
        ),
        confidence=confidence,
        has_contract_evidence=bool(contract_evidence),
        contract_backed_current=(
            status is RelationshipStatus.ACTIVE
            and bool(contract_evidence)
            and role_can_be_contract_backed_incumbent(preferred.role)
        ),
        next_renewal_at=min(renewals) if renewals else None,
        has_role_conflict=role_conflict,
        has_dispute=bool(disputes),
        has_correction=bool(corrections),
        has_retraction=bool(retractions),
        historical_only=bool(evidence)
        and all(snapshot.is_historical_at(now) for snapshot in evidence),
    )


def _relationship_status(
    assertions: tuple[RelationshipEvidenceSnapshot, ...],
    disputes: tuple[RelationshipEvidenceSnapshot, ...],
    corrections: tuple[RelationshipEvidenceSnapshot, ...],
    retractions: tuple[RelationshipEvidenceSnapshot, ...],
    *,
    role_conflict: bool,
    now: datetime,
) -> RelationshipStatus:
    if role_conflict:
        return RelationshipStatus.UNDER_REVIEW
    current = tuple(snapshot for snapshot in assertions if snapshot.is_current_at(now))
    active = tuple(
        snapshot
        for snapshot in current
        if snapshot.supports_active_relationship_at(now)
    )
    if disputes and current:
        return RelationshipStatus.DISPUTED
    if active:
        return RelationshipStatus.ACTIVE
    claimed = tuple(
        snapshot
        for snapshot in current
        if snapshot.evidence_class is RelationshipEvidenceClass.CLAIMED
    )
    if claimed:
        return RelationshipStatus.CLAIMED
    inferred = tuple(
        snapshot
        for snapshot in current
        if snapshot.evidence_class is RelationshipEvidenceClass.INFERRED
    )
    if inferred:
        return RelationshipStatus.INFERRED
    if assertions and all(snapshot.is_stale_at(now) for snapshot in assertions):
        return RelationshipStatus.STALE
    if assertions and all(snapshot.is_historical_at(now) for snapshot in assertions):
        return RelationshipStatus.HISTORICAL
    if retractions:
        return RelationshipStatus.RETRACTED
    if corrections:
        return RelationshipStatus.CORRECTED
    if disputes:
        return RelationshipStatus.DISPUTED
    return RelationshipStatus.UNDER_REVIEW


def _preferred_snapshot(
    evidence: tuple[RelationshipEvidenceSnapshot, ...],
    *,
    now: datetime,
) -> RelationshipEvidenceSnapshot:
    return min(
        evidence,
        key=lambda item: (
            item.claim_type is not RelationshipClaimType.ASSERTION,
            not item.is_current_at(now),
            -_EVIDENCE_PRIORITY[item.evidence_class],
            -item.confidence,
            -item.modified_at.timestamp(),
        ),
    )


def _organization_link(
    evidence: tuple[RelationshipEvidenceSnapshot, ...],
    *,
    source: bool,
) -> tuple[UUID | None, RelationshipOrganizationLinkStatus]:
    active_evidence = tuple(snapshot for snapshot in evidence if snapshot.active)
    candidates = active_evidence or evidence
    pairs = tuple(
        (
            snapshot.source_organization_id if source else snapshot.target_organization_id,
            snapshot.source_link_status if source else snapshot.target_link_status,
        )
        for snapshot in candidates
    )
    exact_ids = {
        organization_id
        for organization_id, status in pairs
        if status is RelationshipOrganizationLinkStatus.EXACT and organization_id is not None
    }
    if len(exact_ids) > 1:
        return None, RelationshipOrganizationLinkStatus.REVIEW_REQUIRED
    if len(exact_ids) == 1:
        return next(iter(exact_ids)), RelationshipOrganizationLinkStatus.EXACT
    strongest = max((status for _, status in pairs), key=_LINK_PRIORITY.__getitem__)
    return None, strongest


def _claimed_names(
    evidence: tuple[RelationshipEvidenceSnapshot, ...],
    *,
    source: bool,
) -> tuple[str, ...]:
    values = {
        snapshot.claimed_source_organization_name
        if source
        else snapshot.claimed_target_organization_name
        for snapshot in evidence
    }
    return tuple(sorted(value for value in values if value is not None))


def _of_type(
    evidence: tuple[RelationshipEvidenceSnapshot, ...],
    claim_type: RelationshipClaimType,
) -> tuple[RelationshipEvidenceSnapshot, ...]:
    return tuple(snapshot for snapshot in evidence if snapshot.claim_type is claim_type)


def _minimum_time(values: Iterable[datetime | None]) -> datetime | None:
    present = tuple(value for value in values if value is not None)
    return min(present) if present else None


def _maximum_time(values: Iterable[datetime | None]) -> datetime | None:
    present = tuple(value for value in values if value is not None)
    return max(present) if present else None

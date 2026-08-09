from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Protocol, TypeVar

from cip.modules.professional_context.domain.community import PublicCommunityContext
from cip.modules.professional_context.domain.contacts import ProfessionalContactEvidence
from cip.modules.professional_context.domain.enums import (
    EmploymentState,
    ProfessionalReviewState,
)
from cip.modules.professional_context.domain.person import ProfessionalPersonReference
from cip.modules.professional_context.domain.projections import (
    ProfessionalContactProjection,
    ProfessionalPersonProjection,
    ProfessionalRoleProjection,
    PublicCommunityProjection,
    ReportingLineProjection,
)
from cip.modules.professional_context.domain.roles import (
    ProfessionalRoleClaim,
    ReportingLineClaim,
)
from cip.modules.professional_context.domain.validation import aware_time


class _Revision(Protocol):
    source_id: str
    source_record_key: str
    supersedes_record_key: str | None
    observed_at: datetime


RevisionT = TypeVar("RevisionT", bound=_Revision)


def reconcile_person_references(
    references: Iterable[ProfessionalPersonReference],
    *,
    now: datetime,
) -> ProfessionalPersonProjection:
    items = tuple(references)
    if not items:
        raise ValueError("at least one professional person reference is required")
    _require_same((item.person_key for item in items), "person_key")
    current = aware_time(now, "now")
    latest = max(items, key=lambda item: item.observed_at)
    visible = latest.visible and latest.processing.permits_processing_at(current)
    return ProfessionalPersonProjection(
        person_key=latest.person_key,
        display_name=latest.display_name,
        source_id=latest.source_id,
        confidence=latest.confidence,
        review_state=latest.review_state,
        lawful_basis=latest.processing.lawful_basis,
        lawful_basis_reference=latest.processing.lawful_basis_reference,
        purpose=latest.processing.purpose,
        current=visible,
        suppressed=latest.suppressed,
        deleted=latest.deleted,
        last_observed_at=latest.observed_at,
        retention_until=latest.processing.retention_until,
    )


def reconcile_role_claims(
    claims: Iterable[ProfessionalRoleClaim],
    *,
    now: datetime,
) -> ProfessionalRoleProjection:
    items = tuple(claims)
    if not items:
        raise ValueError("at least one professional role claim is required")
    _require_same((item.claim_key for item in items), "claim_key")
    _require_same((item.person_key for item in items), "person_key")
    current = aware_time(now, "now")
    effective = _effective_revisions(items)
    latest = max(effective, key=lambda item: item.observed_at)
    current_items = tuple(
        item
        for item in effective
        if item.employment_state_at(current) is EmploymentState.CURRENT
        and item.processing.permits_processing_at(current)
    )
    basis = max(current_items, key=lambda item: item.observed_at) if current_items else latest
    conflict = _role_conflict(current_items)
    review_state = (
        ProfessionalReviewState.REVIEW_REQUIRED
        if conflict
        else _review_state(tuple(item.review_state for item in effective))
    )
    return ProfessionalRoleProjection(
        claim_key=basis.claim_key,
        person_key=basis.person_key,
        organization_id=basis.organization_id if not conflict else None,
        claimed_organization_name=basis.claimed_organization_name,
        role_title=basis.role_title,
        team_name=basis.team_name,
        employment_state=(
            EmploymentState.CURRENT
            if current_items
            else latest.employment_state_at(current)
        ),
        confidence=max(item.confidence for item in (current_items or effective)),
        review_state=review_state,
        lawful_basis=basis.processing.lawful_basis,
        lawful_basis_reference=basis.processing.lawful_basis_reference,
        purpose=basis.processing.purpose,
        suppressed=latest.suppressed,
        deleted=latest.deleted,
        evidence_count=len(effective),
        first_observed_at=min(item.observed_at for item in items),
        last_observed_at=max(item.observed_at for item in items),
        retention_until=max(item.processing.retention_until for item in effective),
    )


def reconcile_reporting_claims(
    claims: Iterable[ReportingLineClaim],
    *,
    now: datetime,
) -> ReportingLineProjection:
    items = tuple(claims)
    if not items:
        raise ValueError("at least one reporting-line claim is required")
    _require_same((item.claim_key for item in items), "claim_key")
    _require_same((item.subject_person_key for item in items), "subject_person_key")
    _require_same((item.manager_person_key for item in items), "manager_person_key")
    current = aware_time(now, "now")
    effective = _effective_revisions(items)
    latest = max(effective, key=lambda item: item.observed_at)
    live = tuple(item for item in effective if _reporting_current(item, current))
    basis = max(live, key=lambda item: item.observed_at) if live else latest
    return ReportingLineProjection(
        claim_key=basis.claim_key,
        subject_person_key=basis.subject_person_key,
        manager_person_key=basis.manager_person_key,
        organization_id=basis.organization_id,
        confidence=max(item.confidence for item in (live or effective)),
        review_state=_review_state(tuple(item.review_state for item in effective)),
        lawful_basis=basis.processing.lawful_basis,
        lawful_basis_reference=basis.processing.lawful_basis_reference,
        purpose=basis.processing.purpose,
        current=bool(live),
        suppressed=latest.suppressed,
        deleted=latest.deleted,
        first_observed_at=min(item.observed_at for item in items),
        last_observed_at=max(item.observed_at for item in items),
        retention_until=max(item.processing.retention_until for item in effective),
    )


def reconcile_contact_evidence(
    evidence: Iterable[ProfessionalContactEvidence],
    *,
    now: datetime,
) -> ProfessionalContactProjection:
    items = tuple(evidence)
    if not items:
        raise ValueError("at least one professional contact evidence record is required")
    _require_same((item.contact_key for item in items), "contact_key")
    current = aware_time(now, "now")
    effective = _effective_revisions(items)
    live = tuple(
        item
        for item in effective
        if item.current_evidence and item.processing.permits_processing_at(current)
    )
    latest = max(effective, key=lambda item: item.observed_at)
    basis = max(live, key=lambda item: item.observed_at) if live else latest
    conflict = len({(item.channel_type, item.value) for item in live}) > 1
    return ProfessionalContactProjection(
        contact_key=basis.contact_key,
        channel_type=basis.channel_type,
        value=basis.value,
        organization_id=basis.organization_id,
        person_key=basis.person_key,
        confidence=max(item.confidence for item in (live or effective)),
        review_state=(
            ProfessionalReviewState.REVIEW_REQUIRED
            if conflict
            else _review_state(tuple(item.review_state for item in effective))
        ),
        lawful_basis=basis.processing.lawful_basis,
        lawful_basis_reference=basis.processing.lawful_basis_reference,
        purpose=basis.processing.purpose,
        current=bool(live) and not conflict,
        suppressed=latest.suppressed,
        deleted=latest.deleted,
        last_observed_at=max(item.observed_at for item in items),
        retention_until=max(item.processing.retention_until for item in effective),
    )


def reconcile_community_context(
    contexts: Iterable[PublicCommunityContext],
    *,
    now: datetime,
) -> PublicCommunityProjection:
    items = tuple(contexts)
    if not items:
        raise ValueError("at least one public community context record is required")
    _require_same((item.context_key for item in items), "context_key")
    current = aware_time(now, "now")
    effective = _effective_revisions(items)
    live = tuple(
        item
        for item in effective
        if item.current_evidence and item.processing.permits_processing_at(current)
    )
    latest = max(effective, key=lambda item: item.observed_at)
    basis = max(live, key=lambda item: item.observed_at) if live else latest
    conflict = len({(item.context_type, item.context_value) for item in live}) > 1
    return PublicCommunityProjection(
        context_key=basis.context_key,
        community_name=basis.community_name,
        context_type=basis.context_type,
        context_value=basis.context_value,
        acquisition_mode=basis.acquisition_mode,
        organization_id=basis.organization_id,
        person_key=basis.person_key,
        confidence=max(item.confidence for item in (live or effective)),
        review_state=(
            ProfessionalReviewState.REVIEW_REQUIRED
            if conflict
            else _review_state(tuple(item.review_state for item in effective))
        ),
        lawful_basis=basis.processing.lawful_basis,
        lawful_basis_reference=basis.processing.lawful_basis_reference,
        purpose=basis.processing.purpose,
        current=bool(live) and not conflict,
        suppressed=latest.suppressed,
        deleted=latest.deleted,
        last_observed_at=max(item.observed_at for item in items),
        retention_until=max(item.processing.retention_until for item in effective),
    )


def _effective_revisions(items: tuple[RevisionT, ...]) -> tuple[RevisionT, ...]:
    superseded = {
        (item.source_id, item.supersedes_record_key)
        for item in items
        if item.supersedes_record_key is not None
    }
    latest_by_record: dict[tuple[str, str], RevisionT] = {}
    for item in sorted(items, key=lambda candidate: candidate.observed_at):
        latest_by_record[(item.source_id, item.source_record_key)] = item
    effective = tuple(
        item for identity, item in latest_by_record.items() if identity not in superseded
    )
    return effective or (max(items, key=lambda item: item.observed_at),)


def _reporting_current(item: ReportingLineClaim, now: datetime) -> bool:
    if not item.current_evidence or not item.processing.permits_processing_at(now):
        return False
    if item.valid_from is not None and item.valid_from > now:
        return False
    return item.valid_until is None or item.valid_until > now


def _role_conflict(items: tuple[ProfessionalRoleClaim, ...]) -> bool:
    if len(items) < 2:
        return False
    identities = {
        (item.organization_id, item.role_title.casefold(), (item.team_name or "").casefold())
        for item in items
    }
    return len(identities) > 1


def _review_state(states: tuple[ProfessionalReviewState, ...]) -> ProfessionalReviewState:
    if ProfessionalReviewState.REVIEW_REQUIRED in states:
        return ProfessionalReviewState.REVIEW_REQUIRED
    if states and all(state is ProfessionalReviewState.REJECTED for state in states):
        return ProfessionalReviewState.REJECTED
    if ProfessionalReviewState.CONFIRMED in states:
        return ProfessionalReviewState.CONFIRMED
    return ProfessionalReviewState.UNREVIEWED


def _require_same(values: Iterable[object], label: str) -> None:
    items = tuple(values)
    if len(set(items)) != 1:
        raise ValueError(f"professional evidence must share {label}")

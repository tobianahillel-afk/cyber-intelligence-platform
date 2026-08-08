from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.corporate_graph.domain.models import GraphNodeType
from cip.modules.corporate_graph.domain.resolution import (
    EntityResolutionCandidate,
    ResolutionCandidateState,
    ResolutionMethod,
)
from cip.modules.corporate_graph.infrastructure.models import (
    CorporateGraphNodeRecord,
    EntityResolutionCandidateRecord,
)
from cip.modules.corporate_graph.infrastructure.projection_hydration import node_snapshots
from cip.modules.corporate_graph.infrastructure.resolution_persistence import (
    persist_resolution_candidate,
)
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.shared.kernel.time import require_aware_utc


def generate_resolution_candidates(
    session: Session,
    *,
    now: datetime,
) -> tuple[EntityResolutionCandidateRecord, ...]:
    generated_at = require_aware_utc(now, field_name="now")
    organizations = tuple(session.scalars(select(OrganizationRecord)).all())
    unresolved_nodes = tuple(
        session.scalars(
            select(CorporateGraphNodeRecord).where(
                CorporateGraphNodeRecord.organization_id.is_(None),
                CorporateGraphNodeRecord.suppressed.is_(False),
            )
        )
    )
    records: list[EntityResolutionCandidateRecord] = []
    for node in unresolved_nodes:
        candidates = _candidates_for_node(session, node, organizations, now=generated_at)
        current_keys = {
            (candidate.candidate_organization_id, candidate.method.value)
            for candidate in candidates
        }
        for candidate in candidates:
            records.append(
                persist_resolution_candidate(session, candidate, now=generated_at)
            )
        _supersede_stale_candidates(
            session,
            node_key=node.node_key,
            current_keys=current_keys,
            now=generated_at,
        )
    session.flush()
    return tuple(records)


def _candidates_for_node(
    session: Session,
    node: CorporateGraphNodeRecord,
    organizations: tuple[OrganizationRecord, ...],
    *,
    now: datetime,
) -> tuple[EntityResolutionCandidate, ...]:
    exact_ids = _snapshot_organization_ids(session, node, now=now)
    if exact_ids:
        return tuple(
            _candidate(
                node=node,
                organization_id=organization_id,
                method=ResolutionMethod.EXACT_SOURCE_BINDING,
                score=1.0,
                reason="current source snapshots reference this canonical organization",
                conflicts=tuple(value for value in exact_ids if value != organization_id),
                now=now,
            )
            for organization_id in exact_ids
        )
    if node.node_type == GraphNodeType.DOMAIN.value:
        domain_matches = _domain_matches(node.display_name, organizations)
        if domain_matches:
            return tuple(
                _candidate(
                    node=node,
                    organization_id=organization.id,
                    method=ResolutionMethod.DOMAIN_OWNERSHIP,
                    score=0.85,
                    reason="declared organization website matches the graph domain",
                    conflicts=tuple(
                        value.id for value in domain_matches if value.id != organization.id
                    ),
                    now=now,
                )
                for organization in domain_matches
            )
    name_matches = _name_matches(node.display_name, organizations)
    return tuple(
        _candidate(
            node=node,
            organization_id=organization.id,
            method=ResolutionMethod.PROBABILISTIC_CONTEXT,
            score=0.65,
            reason="normalized organization name matches without a deterministic identifier",
            conflicts=tuple(value.id for value in name_matches if value.id != organization.id),
            now=now,
        )
        for organization in name_matches
    )


def _snapshot_organization_ids(
    session: Session,
    node: CorporateGraphNodeRecord,
    *,
    now: datetime,
) -> tuple[UUID, ...]:
    values = {
        snapshot.organization_id
        for snapshot in node_snapshots(session, node.id)
        if snapshot.organization_id is not None and snapshot.is_current_at(now)
    }
    return tuple(sorted(values, key=str))


def _candidate(
    *,
    node: CorporateGraphNodeRecord,
    organization_id: UUID,
    method: ResolutionMethod,
    score: float,
    reason: str,
    conflicts: tuple[UUID, ...],
    now: datetime,
) -> EntityResolutionCandidate:
    return EntityResolutionCandidate(
        node_key=node.node_key,
        candidate_organization_id=organization_id,
        method=method,
        score=score,
        reasons=(reason,),
        created_at=now,
        state=ResolutionCandidateState.PENDING,
        conflicting_organization_ids=conflicts,
        requires_review=True,
    )


def _name_matches(
    display_name: str,
    organizations: tuple[OrganizationRecord, ...],
) -> tuple[OrganizationRecord, ...]:
    wanted = _normalize_name(display_name)
    if not wanted:
        return ()
    return tuple(
        organization
        for organization in organizations
        if wanted
        in {
            _normalize_name(organization.canonical_name),
            _normalize_name(organization.legal_name or ""),
        }
    )


def _domain_matches(
    display_name: str,
    organizations: tuple[OrganizationRecord, ...],
) -> tuple[OrganizationRecord, ...]:
    wanted = _normalize_domain(display_name)
    if wanted is None:
        return ()
    return tuple(
        organization
        for organization in organizations
        if _normalize_domain(organization.website_url) == wanted
    )


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _normalize_domain(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    raw = value.strip()
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    if parsed.hostname is None:
        return None
    hostname = parsed.hostname.casefold().rstrip(".")
    return hostname[4:] if hostname.startswith("www.") else hostname


def _supersede_stale_candidates(
    session: Session,
    *,
    node_key: str,
    current_keys: set[tuple[UUID, str]],
    now: datetime,
) -> None:
    records = session.scalars(
        select(EntityResolutionCandidateRecord).where(
            EntityResolutionCandidateRecord.node_key == node_key,
            EntityResolutionCandidateRecord.state == ResolutionCandidateState.PENDING.value,
        )
    )
    for record in records:
        if (record.candidate_organization_id, record.method) not in current_keys:
            record.state = ResolutionCandidateState.SUPERSEDED.value
            record.requires_review = False
            record.updated_at = now

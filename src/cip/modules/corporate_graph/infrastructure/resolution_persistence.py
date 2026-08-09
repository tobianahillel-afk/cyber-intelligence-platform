from __future__ import annotations

import json
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.corporate_graph.domain.blast_radius import BlastRadiusPreview
from cip.modules.corporate_graph.domain.resolution import (
    EntityResolutionCandidate,
    ResolutionCandidateState,
    ResolutionDecision,
    ResolutionDecisionType,
)
from cip.modules.corporate_graph.infrastructure.models import (
    CorporateGraphNodeRecord,
    EntityResolutionBindingRecord,
    EntityResolutionCandidateRecord,
    EntityResolutionDecisionRecord,
)
from cip.modules.corporate_graph.infrastructure.node_state import refresh_node_state
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.shared.kernel.time import require_aware_utc


def persist_resolution_candidate(
    session: Session,
    candidate: EntityResolutionCandidate,
    *,
    now: datetime,
) -> EntityResolutionCandidateRecord:
    persisted_at = require_aware_utc(now, field_name="now")
    _require_node(session, candidate.node_key)
    _require_organization(session, candidate.candidate_organization_id)
    record = session.scalar(
        select(EntityResolutionCandidateRecord).where(
            EntityResolutionCandidateRecord.node_key == candidate.node_key,
            EntityResolutionCandidateRecord.candidate_organization_id
            == candidate.candidate_organization_id,
            EntityResolutionCandidateRecord.method == candidate.method.value,
        )
    )
    if record is None:
        identity = (
            f"entity-resolution-candidate:{candidate.node_key}:"
            f"{candidate.candidate_organization_id}:{candidate.method.value}"
        )
        record = EntityResolutionCandidateRecord(
            id=uuid5(NAMESPACE_URL, identity),
            node_key=candidate.node_key,
            candidate_organization_id=candidate.candidate_organization_id,
            method=candidate.method.value,
            score=candidate.score,
            reasons_json=_uuid_safe_json(candidate.reasons),
            conflicting_organization_ids_json=_uuid_safe_json(
                candidate.conflicting_organization_ids
            ),
            state=candidate.state.value,
            requires_review=candidate.requires_review,
            created_at=persisted_at,
            updated_at=persisted_at,
        )
        session.add(record)
    else:
        if record.state in {
            ResolutionCandidateState.CONFIRMED.value,
            ResolutionCandidateState.REJECTED.value,
        }:
            return record
        record.score = candidate.score
        record.reasons_json = _uuid_safe_json(candidate.reasons)
        record.conflicting_organization_ids_json = _uuid_safe_json(
            candidate.conflicting_organization_ids
        )
        record.state = candidate.state.value
        record.requires_review = candidate.requires_review
        record.updated_at = persisted_at
    session.flush()
    return record


def record_resolution_decision(
    session: Session,
    decision: ResolutionDecision,
    *,
    preview: BlastRadiusPreview,
    now: datetime,
) -> EntityResolutionDecisionRecord:
    persisted_at = require_aware_utc(now, field_name="now")
    candidate = session.get(EntityResolutionCandidateRecord, decision.candidate_id)
    if candidate is None:
        raise ValueError("resolution candidate does not exist")
    if candidate.node_key != decision.node_key:
        raise ValueError("resolution decision node does not match candidate")
    if preview.node_key != decision.node_key:
        raise ValueError("blast-radius preview node does not match decision")
    if decision.organization_id is not None:
        expected_target = f"organization:{decision.organization_id}"
        if preview.target_organization_key != expected_target:
            raise ValueError("blast-radius preview target does not match decision")
        _require_organization(session, decision.organization_id)
    if preview.fingerprint != decision.blast_radius_fingerprint:
        raise ValueError("blast-radius preview changed; refresh before deciding")
    if decision.reverses_decision_id is not None:
        prior = session.get(EntityResolutionDecisionRecord, decision.reverses_decision_id)
        if prior is None or prior.node_key != decision.node_key:
            raise ValueError("reversed resolution decision is missing or belongs to another node")
    existing = session.get(EntityResolutionDecisionRecord, decision.decision_id)
    if existing is not None:
        return existing
    record = EntityResolutionDecisionRecord(
        id=decision.decision_id,
        candidate_id=decision.candidate_id,
        node_key=decision.node_key,
        decision_type=decision.decision_type.value,
        actor=decision.actor,
        reason=decision.reason,
        organization_id=decision.organization_id,
        reverses_decision_id=decision.reverses_decision_id,
        blast_radius_fingerprint=decision.blast_radius_fingerprint or "",
        decided_at=decision.decided_at,
        created_at=persisted_at,
    )
    session.add(record)
    _apply_candidate_state(candidate, decision.decision_type, now=persisted_at)
    _apply_binding(session, candidate, record, decision, now=persisted_at)
    session.flush()
    _refresh_decision_node(session, decision.node_key, now=persisted_at)
    session.flush()
    return record


def _apply_candidate_state(
    candidate: EntityResolutionCandidateRecord,
    decision_type: ResolutionDecisionType,
    *,
    now: datetime,
) -> None:
    if decision_type in {
        ResolutionDecisionType.MERGE,
        ResolutionDecisionType.OVERRIDE,
        ResolutionDecisionType.RESTORE,
    }:
        candidate.state = ResolutionCandidateState.CONFIRMED.value
    elif decision_type is ResolutionDecisionType.REJECT:
        candidate.state = ResolutionCandidateState.REJECTED.value
    else:
        candidate.state = ResolutionCandidateState.SUPERSEDED.value
    candidate.requires_review = False
    candidate.updated_at = now


def _apply_binding(
    session: Session,
    candidate: EntityResolutionCandidateRecord,
    record: EntityResolutionDecisionRecord,
    decision: ResolutionDecision,
    *,
    now: datetime,
) -> None:
    binding = session.scalar(
        select(EntityResolutionBindingRecord).where(
            EntityResolutionBindingRecord.node_key == decision.node_key
        )
    )
    if decision.decision_type in {
        ResolutionDecisionType.REJECT,
        ResolutionDecisionType.SPLIT,
    }:
        if decision.decision_type is ResolutionDecisionType.SPLIT and binding is not None:
            binding.current = False
            binding.decision_id = record.id
            binding.updated_at = now
        return
    if decision.organization_id is None:
        raise ValueError("binding decision requires organization_id")
    if binding is None:
        binding = EntityResolutionBindingRecord(
            id=uuid5(NAMESPACE_URL, f"entity-resolution-binding:{decision.node_key}"),
            node_key=decision.node_key,
            organization_id=decision.organization_id,
            candidate_id=candidate.id,
            decision_id=record.id,
            method=candidate.method,
            confidence=candidate.score,
            current=True,
            bound_at=decision.decided_at,
            updated_at=now,
        )
        session.add(binding)
    else:
        binding.organization_id = decision.organization_id
        binding.candidate_id = candidate.id
        binding.decision_id = record.id
        binding.method = candidate.method
        binding.confidence = candidate.score
        binding.current = True
        binding.bound_at = decision.decided_at
        binding.updated_at = now


def _refresh_decision_node(session: Session, node_key: str, *, now: datetime) -> None:
    node_id = session.scalar(
        select(CorporateGraphNodeRecord.id).where(CorporateGraphNodeRecord.node_key == node_key)
    )
    if node_id is None:
        raise ValueError("resolution decision references missing graph node")
    refresh_node_state(session, node_id, now=now)


def _require_node(session: Session, node_key: str) -> None:
    if session.scalar(
        select(CorporateGraphNodeRecord.id).where(CorporateGraphNodeRecord.node_key == node_key)
    ) is None:
        raise ValueError("resolution candidate references missing graph node")


def _require_organization(session: Session, organization_id: UUID) -> None:
    if session.get(OrganizationRecord, organization_id) is None:
        raise ValueError("resolution candidate references missing organization")


def _uuid_safe_json(values: tuple[object, ...]) -> str:
    return json.dumps([str(value) for value in values], separators=(",", ":"))

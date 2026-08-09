from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.research_orchestration.infrastructure.models import (
    ResearchResultRecord,
    ResearchStepAttemptRecord,
    ResearchStepRecord,
)
from cip.modules.research_orchestration.infrastructure.payloads import result_key
from cip.shared.kernel.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class ResearchResultCapture:
    attempt_id: UUID | None
    result_type: str
    evidence_reference: str
    provenance_reference: str
    source_id: str
    summary: str | None
    recorded_by: str


def record_research_result(
    session: Session,
    plan_id: UUID,
    step_key: str,
    capture: ResearchResultCapture,
    *,
    now: datetime,
) -> ResearchResultRecord:
    current = require_aware_utc(now, field_name="now")
    step = _step(session, plan_id, step_key)
    normalized_type = _required(capture.result_type, "result_type", 60)
    evidence = _required(capture.evidence_reference, "evidence_reference", 500)
    provenance = _required(capture.provenance_reference, "provenance_reference", 500)
    normalized_source = _required(capture.source_id, "source_id", 100)
    actor = _required(capture.recorded_by, "recorded_by", 200)
    normalized_summary = _optional(capture.summary, "summary", 1000)
    _validate_attempt(
        session,
        capture.attempt_id,
        plan_id=plan_id,
        step_id=step.id,
    )
    key = result_key(
        plan_id=plan_id,
        step_key=step.step_key,
        result_type=normalized_type,
        evidence_reference=evidence,
        provenance_reference=provenance,
    )
    existing = session.scalar(
        select(ResearchResultRecord).where(ResearchResultRecord.result_key == key)
    )
    if existing is not None:
        return existing
    record = ResearchResultRecord(
        id=uuid4(),
        plan_id=plan_id,
        step_id=step.id,
        attempt_id=capture.attempt_id,
        result_key=key,
        result_type=normalized_type,
        evidence_reference=evidence,
        provenance_reference=provenance,
        source_id=normalized_source,
        summary=normalized_summary,
        recorded_by=actor,
        recorded_at=current,
    )
    session.add(record)
    session.flush()
    return record


def _step(session: Session, plan_id: UUID, step_key: str) -> ResearchStepRecord:
    normalized = _required(step_key, "step_key", 150)
    record = session.scalar(
        select(ResearchStepRecord).where(
            ResearchStepRecord.plan_id == plan_id,
            ResearchStepRecord.step_key == normalized,
        )
    )
    if record is None:
        raise LookupError("research step not found")
    return record


def _validate_attempt(
    session: Session,
    attempt_id: UUID | None,
    *,
    plan_id: UUID,
    step_id: UUID,
) -> None:
    if attempt_id is None:
        return
    attempt = session.get(ResearchStepAttemptRecord, attempt_id)
    if attempt is None:
        raise LookupError("research attempt not found")
    if attempt.plan_id != plan_id or attempt.step_id != step_id:
        raise ValueError("research result attempt does not belong to plan step")


def _required(value: str, field_name: str, maximum: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > maximum:
        raise ValueError(f"{field_name} cannot exceed {maximum} characters")
    return normalized


def _optional(value: str | None, field_name: str, maximum: int) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > maximum:
        raise ValueError(f"{field_name} cannot exceed {maximum} characters")
    return normalized

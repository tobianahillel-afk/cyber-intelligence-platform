from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from cip.modules.evidence.infrastructure.models import EvidenceRecord
from cip.modules.raw_observations.infrastructure.models import RawObservationRecord
from cip.modules.research_orchestration.infrastructure.result_persistence import (
    ResearchResultCapture,
)

_EVIDENCE_PREFIX = "evidence:"
_RAW_OBSERVATION_PREFIX = "raw-observation:"
_SOURCE_RECORD_PREFIX = "source-record:"


def validate_research_result_capture(
    session: Session,
    capture: ResearchResultCapture,
    *,
    expected_source_id: str,
) -> EvidenceRecord:
    if capture.source_id != expected_source_id:
        raise ValueError("research capture source does not match step source")
    evidence = _evidence(session, capture.evidence_reference)
    if evidence.source_id != capture.source_id:
        raise ValueError("research evidence source does not match capture source")
    _validate_provenance(session, evidence, capture.provenance_reference)
    return evidence


def _evidence(session: Session, reference: str) -> EvidenceRecord:
    value = reference.strip()
    if not value.startswith(_EVIDENCE_PREFIX):
        raise ValueError("evidence_reference must use evidence:<uuid>")
    evidence_id = _uuid(value.removeprefix(_EVIDENCE_PREFIX), "evidence_reference")
    record = session.get(EvidenceRecord, evidence_id)
    if record is None:
        raise LookupError("research evidence reference not found")
    return record


def _validate_provenance(
    session: Session,
    evidence: EvidenceRecord,
    reference: str,
) -> None:
    value = reference.strip()
    if value.startswith(_SOURCE_RECORD_PREFIX):
        _validate_source_record(evidence, value.removeprefix(_SOURCE_RECORD_PREFIX))
        return
    if value.startswith(_RAW_OBSERVATION_PREFIX):
        _validate_raw_observation(
            session,
            evidence,
            value.removeprefix(_RAW_OBSERVATION_PREFIX),
        )
        return
    raise ValueError("unsupported provenance_reference")


def _validate_source_record(evidence: EvidenceRecord, source_record_key: str) -> None:
    normalized = source_record_key.strip()
    if not normalized or evidence.source_record_key != normalized:
        raise ValueError("source-record provenance does not match evidence")


def _validate_raw_observation(
    session: Session,
    evidence: EvidenceRecord,
    raw_id: str,
) -> None:
    observation_id = _uuid(raw_id, "provenance_reference")
    observation = session.get(RawObservationRecord, observation_id)
    if observation is None:
        raise LookupError("research provenance observation not found")
    if observation.source_id != evidence.source_id:
        raise ValueError("provenance source does not match evidence source")
    if (
        evidence.source_record_key is None
        or observation.source_record_key != evidence.source_record_key
    ):
        raise ValueError("provenance source record does not match evidence")


def _uuid(value: str, field_name: str) -> UUID:
    try:
        return UUID(value.strip())
    except ValueError as exc:
        raise ValueError(f"{field_name} contains an invalid uuid") from exc

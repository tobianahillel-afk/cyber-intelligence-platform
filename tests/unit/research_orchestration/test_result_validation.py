from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from cip.modules.evidence.infrastructure.models import EvidenceRecord
from cip.modules.raw_observations.infrastructure.models import RawObservationRecord
from cip.modules.research_orchestration.infrastructure.result_persistence import (
    ResearchResultCapture,
)
from cip.modules.research_orchestration.infrastructure.result_validation import (
    validate_research_result_capture,
)
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.persistence import sync_source_registry
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 9, 17, 0, tzinfo=UTC)
SOURCE_ID = "validated-research-source"
EVIDENCE_ID = UUID("ffffffff-ffff-4fff-8fff-fffffffffff1")
OBSERVATION_ID = UUID("ffffffff-ffff-4fff-8fff-fffffffffff2")
SOURCE_RECORD_KEY = "provider-record-42"


def test_source_record_provenance_must_match_existing_evidence() -> None:
    session = _session_with_evidence()

    evidence = _validate(
        session,
        _capture(provenance_reference=f"source-record:{SOURCE_RECORD_KEY}"),
    )

    assert evidence.id == EVIDENCE_ID


def test_raw_observation_provenance_must_match_source_and_record() -> None:
    session = _session_with_evidence()
    session.add(_observation())
    session.flush()

    evidence = _validate(
        session,
        _capture(provenance_reference=f"raw-observation:{OBSERVATION_ID}"),
    )

    assert evidence.source_record_key == SOURCE_RECORD_KEY


def test_missing_or_arbitrary_references_fail_closed() -> None:
    session = _session_with_evidence()

    with pytest.raises(ValueError, match="evidence:<uuid>"):
        _validate(session, _capture(evidence_reference="public-resource:42"))
    with pytest.raises(LookupError, match="evidence reference not found"):
        _validate(
            session,
            _capture(
                evidence_reference="evidence:ffffffff-ffff-4fff-8fff-fffffffffff9"
            ),
        )
    with pytest.raises(ValueError, match="unsupported provenance"):
        _validate(
            session,
            _capture(provenance_reference="arbitrary:reference"),
        )


def test_step_source_capture_source_and_evidence_source_must_match() -> None:
    session = _session_with_evidence()

    with pytest.raises(ValueError, match="capture source does not match step source"):
        _validate(
            session,
            _capture(source_id="different-source"),
        )
    with pytest.raises(ValueError, match="capture source does not match step source"):
        _validate(
            session,
            _capture(),
            expected_source_id="different-step-source",
        )


def test_provenance_mismatch_is_rejected() -> None:
    session = _session_with_evidence()

    with pytest.raises(ValueError, match="source-record provenance"):
        _validate(
            session,
            _capture(provenance_reference="source-record:different-record"),
        )


def test_raw_observation_with_different_record_is_rejected() -> None:
    session = _session_with_evidence()
    session.add(_observation(source_record_key="different-record"))
    session.flush()

    with pytest.raises(ValueError, match="source record"):
        _validate(
            session,
            _capture(provenance_reference=f"raw-observation:{OBSERVATION_ID}"),
        )


def _validate(
    session: Session,
    capture: ResearchResultCapture,
    *,
    expected_source_id: str = SOURCE_ID,
) -> EvidenceRecord:
    return validate_research_result_capture(
        session,
        capture,
        expected_source_id=expected_source_id,
    )


def _session() -> Session:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return create_session_factory(engine)()


def _session_with_evidence() -> Session:
    session = _session()
    _persist_source(session)
    session.add(
        EvidenceRecord(
            id=EVIDENCE_ID,
            source_id=SOURCE_ID,
            source_record_key=SOURCE_RECORD_KEY,
            source_url="https://research.example.test/results/42",
            summary="Bounded research evidence",
            confidence=0.9,
            collected_at=NOW,
            published_at=None,
            observed_at=NOW,
            content_hash_sha256="a" * 64,
            raw_storage_uri=None,
            raw_storage_permitted=False,
            retention_until=None,
        )
    )
    session.flush()
    return session


def _persist_source(session: Session) -> None:
    policy = SourcePolicy(
        id=SOURCE_ID,
        name="Validated research source",
        base_url="https://research.example.test",
        status=SourceStatus.ENABLED,
        source_type=SourceType.API,
        owner="Research provider",
        allowed_data_categories=frozenset({DataCategory.ORGANIZATION_METADATA}),
        terms_url="https://research.example.test/terms",
        retention_days=90,
        human_review_required=False,
    )
    authorization = SourceAuthorization(
        status=AuthorizationStatus.APPROVED,
        document_reference="approval:validated-research",
        approved_hosts=frozenset({"research.example.test"}),
        approved_path_prefixes=("/results",),
        approved_purposes=frozenset({"organization-research"}),
        automated_collection_allowed=True,
    )
    sync_source_registry(session, (SourceRegistryEntry(policy, authorization, {}),))


def _observation(
    *,
    source_record_key: str = SOURCE_RECORD_KEY,
) -> RawObservationRecord:
    return RawObservationRecord(
        id=OBSERVATION_ID,
        source_id=SOURCE_ID,
        adapter_id="research-adapter",
        adapter_version="1",
        collection_job_id=UUID("ffffffff-ffff-4fff-8fff-fffffffffff3"),
        source_record_key=source_record_key,
        source_record_type="research_result",
        source_record_action="upsert",
        supersedes_observation_id=None,
        source_url="https://research.example.test/results/42",
        collected_at=NOW,
        observed_at=NOW,
        published_at=None,
        source_updated_at=None,
        payload_reference=None,
        payload_hash_sha256="b" * 64,
        schema_fingerprint=None,
        content_language="en",
        data_categories=[DataCategory.ORGANIZATION_METADATA.value],
        classification="internal",
        retention_until=None,
    )


def _capture(
    *,
    evidence_reference: str = f"evidence:{EVIDENCE_ID}",
    provenance_reference: str = f"source-record:{SOURCE_RECORD_KEY}",
    source_id: str = SOURCE_ID,
) -> ResearchResultCapture:
    return ResearchResultCapture(
        attempt_id=None,
        result_type="evidence_reference",
        evidence_reference=evidence_reference,
        provenance_reference=provenance_reference,
        source_id=source_id,
        summary="Bounded analyst summary",
        recorded_by="researcher@example.test",
    )

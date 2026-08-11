from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select

from cip.modules.evidence.infrastructure.models import EvidenceRecord
from cip.modules.opportunities.domain.entities import (
    CommercialSignal,
    NeedHypothesisClass,
    SignalPolarity,
    SignalType,
)
from cip.modules.opportunities.domain.fusion import FusionConfig
from cip.modules.opportunities.infrastructure.fusion_generation import generate_need_hypotheses
from cip.modules.opportunities.infrastructure.hypotheses import hypothesis_from_record
from cip.modules.opportunities.infrastructure.models import NeedHypothesisRecord
from cip.modules.opportunities.infrastructure.signals import store_commercial_signal
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.service_taxonomy.domain.models import CyberServiceFamily
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 11, 10, 30, tzinfo=UTC)
ORG_ID = UUID("10000000-0000-0000-0000-000000000001")
SUPPORT_EVIDENCE_ID = UUID("10000000-0000-0000-0000-000000000002")
CONFLICT_EVIDENCE_ID = UUID("10000000-0000-0000-0000-000000000003")


def test_fused_hypothesis_round_trip_is_idempotent_and_rule_versioned() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)

    with factory() as session:
        _seed_context(session)
        support_id = store_commercial_signal(
            session,
            _signal(
                evidence_id=SUPPORT_EVIDENCE_ID,
                source="source-a",
                confidence=0.86,
            ),
        )
        conflict_id = store_commercial_signal(
            session,
            _signal(
                evidence_id=CONFLICT_EVIDENCE_ID,
                source="source-b",
                confidence=0.72,
                polarity=SignalPolarity.CONTRADICTING,
            ),
        )

        first = generate_need_hypotheses(
            session,
            ORG_ID,
            now=NOW,
            config=FusionConfig(rule_version="1.0.0"),
        )
        replay = generate_need_hypotheses(
            session,
            ORG_ID,
            now=NOW,
            config=FusionConfig(rule_version="1.0.0"),
        )
        revised = generate_need_hypotheses(
            session,
            ORG_ID,
            now=NOW,
            config=FusionConfig(rule_version="1.1.0"),
        )
        session.commit()

        assert first == replay
        assert len(first) == 1
        assert len(revised) == 1
        assert revised != first
        assert session.scalar(select(func.count()).select_from(NeedHypothesisRecord)) == 2

        record = session.get(NeedHypothesisRecord, first[0])
        assert record is not None
        hypothesis = hypothesis_from_record(session, record)
        assert hypothesis.service_families == (CyberServiceFamily.CLOUD_SECURITY,)
        assert hypothesis.hypothesis_class is NeedHypothesisClass.CAPABILITY_GAP
        assert hypothesis.signal_ids == (support_id,)
        assert hypothesis.conflicting_signal_ids == (conflict_id,)
        assert hypothesis.negative_signal_ids == ()
        assert {item.independence_key for item in hypothesis.source_contributions} == {
            "source:source-a",
            "source:source-b",
        }
        assert set(hypothesis.evidence_ids) == {
            SUPPORT_EVIDENCE_ID,
            CONFLICT_EVIDENCE_ID,
        }


def test_hypothesis_hydration_fails_closed_on_invalid_source_contribution_json() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)

    with factory() as session:
        _seed_context(session)
        store_commercial_signal(
            session,
            _signal(
                evidence_id=SUPPORT_EVIDENCE_ID,
                source="source-a",
                confidence=0.8,
            ),
        )
        hypothesis_id = generate_need_hypotheses(session, ORG_ID, now=NOW)[0]
        record = session.get(NeedHypothesisRecord, hypothesis_id)
        assert record is not None
        record.source_contributions = [{"independence_key": 123}]
        session.flush()

        with pytest.raises(ValueError, match="must be a non-empty string"):
            hypothesis_from_record(session, record)


def _seed_context(session) -> None:
    session.add(
        OrganizationRecord(
            id=ORG_ID,
            canonical_name="Example Cloud Organization",
            legal_name="Example Cloud Organization",
            country_code="FR",
            website_url="https://example.invalid",
            registration_ids=[],
            created_at=NOW,
            updated_at=NOW,
        )
    )
    session.add_all(
        (
            _evidence(SUPPORT_EVIDENCE_ID, "source-a", "support"),
            _evidence(CONFLICT_EVIDENCE_ID, "source-b", "conflict"),
        )
    )
    session.flush()


def _evidence(evidence_id: UUID, source_id: str, key: str) -> EvidenceRecord:
    return EvidenceRecord(
        id=evidence_id,
        source_id=source_id,
        source_record_key=key,
        source_url=f"https://{source_id}.example/{key}",
        summary=f"{key} evidence",
        confidence=0.9,
        collected_at=NOW - timedelta(days=1),
        published_at=NOW - timedelta(days=2),
        observed_at=NOW - timedelta(days=2),
        content_hash_sha256=key.ljust(64, "0")[:64],
        raw_storage_uri=None,
        raw_storage_permitted=False,
        retention_until=NOW + timedelta(days=365),
    )


def _signal(
    *,
    evidence_id: UUID,
    source: str,
    confidence: float,
    polarity: SignalPolarity = SignalPolarity.SUPPORTING,
) -> CommercialSignal:
    return CommercialSignal(
        organization_id=ORG_ID,
        evidence_id=evidence_id,
        signal_type=SignalType.CORPORATE_CHANGE,
        title="Cloud security transformation",
        summary="Organization-specific evidence for a cloud security capability gap.",
        confidence=confidence,
        collected_at=NOW - timedelta(days=1),
        published_at=NOW - timedelta(days=2),
        expires_at=NOW + timedelta(days=30),
        service_families=(CyberServiceFamily.CLOUD_SECURITY,),
        hypothesis_classes=(NeedHypothesisClass.CAPABILITY_GAP,),
        independence_key=f"source:{source}",
        polarity=polarity,
        mapping_rule_id="lot24-test-map",
        mapping_rule_version="1.0.0",
    )

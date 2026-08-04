from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cip.modules.evidence.infrastructure.models import EvidenceRecord
from cip.modules.opportunities.domain.entities import (
    CommercialSignal,
    DataQuality,
    OpportunityState,
    ReviewAction,
    SignalType,
)
from cip.modules.opportunities.infrastructure.errors import (
    OpportunityNotFoundError,
    ScoreComponentNotFoundError,
)
from cip.modules.opportunities.infrastructure.generation import generate_siem_soc_opportunity
from cip.modules.opportunities.infrastructure.models import (
    CommercialSignalRecord,
    OpportunityRecord,
    OpportunityReviewRecord,
    OpportunityScoreComponentRecord,
)
from cip.modules.opportunities.infrastructure.queries import (
    get_opportunity_detail,
    list_opportunities,
)
from cip.modules.opportunities.infrastructure.reviews import (
    override_score_component,
    review_opportunity,
)
from cip.modules.opportunities.infrastructure.signals import store_commercial_signal
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 4, 0, 0, tzinfo=UTC)


@pytest.fixture
def session() -> Session:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)
    with factory() as database_session:
        yield database_session


def test_signal_to_opportunity_to_review_pipeline(session: Session) -> None:
    organization_id, evidence_ids = _seed_context(session)
    job = _signal(
        organization_id,
        evidence_ids[0],
        SignalType.JOB_POSTING,
        "Hiring a Microsoft Sentinel SIEM engineer",
        confidence=0.8,
    )
    tender = _signal(
        organization_id,
        evidence_ids[1],
        SignalType.PUBLIC_TENDER,
        "Public SIEM and SOC managed-service tender",
        confidence=0.9,
    )

    assert store_commercial_signal(session, job) == job.id
    assert store_commercial_signal(session, job) == job.id
    opportunity_id = generate_siem_soc_opportunity(session, organization_id, now=NOW)
    assert opportunity_id is not None
    partial = get_opportunity_detail(session, opportunity_id)
    assert partial.opportunity.data_quality == DataQuality.PARTIAL.value
    assert partial.opportunity.evidence_count == 1

    store_commercial_signal(session, tender)
    regenerated_id = generate_siem_soc_opportunity(session, organization_id, now=NOW)
    assert regenerated_id == opportunity_id
    detail = get_opportunity_detail(session, opportunity_id)
    assert detail.opportunity.data_quality == DataQuality.COMPLETE.value
    assert detail.opportunity.evidence_count == 2
    assert detail.opportunity.score > partial.opportunity.score
    assert len(detail.components) == 6
    assert len(detail.evidence) == 2

    page = list_opportunities(
        session,
        now=NOW,
        states=(OpportunityState.NEEDS_REVIEW,),
        min_score=80,
    )
    assert page.total == 1
    assert page.items[0].id == opportunity_id

    state = review_opportunity(
        session,
        opportunity_id,
        ReviewAction.QUALIFY,
        actor="analyst@example.test",
        now=NOW + timedelta(minutes=5),
        note="Evidence checked",
    )
    assert state is OpportunityState.QUALIFIED
    reviewed = get_opportunity_detail(session, opportunity_id)
    assert reviewed.opportunity.state == OpportunityState.QUALIFIED.value
    assert reviewed.reviews[0].actor == "analyst@example.test"

    signal_count = session.scalar(select(func.count()).select_from(CommercialSignalRecord))
    assert signal_count == 2


def test_score_override_survives_automatic_recalculation(session: Session) -> None:
    organization_id, evidence_ids = _seed_context(session)
    store_commercial_signal(
        session,
        _signal(
            organization_id,
            evidence_ids[0],
            SignalType.JOB_POSTING,
            "Hiring a Splunk SIEM engineer",
        ),
    )
    opportunity_id = generate_siem_soc_opportunity(session, organization_id, now=NOW)
    assert opportunity_id is not None
    detail = get_opportunity_detail(session, opportunity_id)
    component = next(item for item in detail.components if item.rule_id == "evidence-confidence")

    overridden_score = override_score_component(
        session,
        opportunity_id,
        component.id,
        actor="reviewer",
        now=NOW + timedelta(minutes=1),
        value=0.1,
        weight=25.0,
        reason="Analyst-calibrated confidence",
    )
    assert overridden_score != detail.opportunity.score

    store_commercial_signal(
        session,
        _signal(
            organization_id,
            evidence_ids[1],
            SignalType.PUBLIC_TENDER,
            "SIEM public tender",
            confidence=0.95,
        ),
    )
    generate_siem_soc_opportunity(session, organization_id, now=NOW + timedelta(minutes=2))
    recalculated = get_opportunity_detail(session, opportunity_id)
    persisted = next(
        item for item in recalculated.components if item.rule_id == "evidence-confidence"
    )

    assert persisted.analyst_overridden is True
    assert persisted.value == 0.1
    assert persisted.weight == 25.0
    assert persisted.original_value == pytest.approx(0.875)
    assert persisted.original_weight == 5.0
    assert persisted.reason == "Analyst-calibrated confidence"
    assert recalculated.opportunity.data_quality == DataQuality.COMPLETE.value


def test_expired_snooze_reopens_when_new_evaluation_arrives(session: Session) -> None:
    organization_id, evidence_ids = _seed_context(session)
    store_commercial_signal(
        session,
        _signal(
            organization_id,
            evidence_ids[0],
            SignalType.PUBLIC_TENDER,
            "SIEM tender",
        ),
    )
    opportunity_id = generate_siem_soc_opportunity(session, organization_id, now=NOW)
    assert opportunity_id is not None
    review_opportunity(
        session,
        opportunity_id,
        ReviewAction.SNOOZE,
        actor="reviewer",
        now=NOW,
        snoozed_until=NOW + timedelta(hours=1),
    )

    generate_siem_soc_opportunity(
        session,
        organization_id,
        now=NOW + timedelta(hours=2),
    )

    record = session.get(OpportunityRecord, opportunity_id)
    assert record is not None
    assert record.state == OpportunityState.NEEDS_REVIEW.value
    assert record.snoozed_until is None


def test_review_and_override_errors(session: Session) -> None:
    missing_id = uuid4()

    with pytest.raises(OpportunityNotFoundError):
        get_opportunity_detail(session, missing_id)
    with pytest.raises(OpportunityNotFoundError):
        review_opportunity(
            session,
            missing_id,
            ReviewAction.QUALIFY,
            actor="analyst",
            now=NOW,
        )
    with pytest.raises(ScoreComponentNotFoundError):
        override_score_component(
            session,
            missing_id,
            uuid4(),
            actor="analyst",
            now=NOW,
            value=0.5,
        )


def test_review_validation_and_component_validation(session: Session) -> None:
    opportunity_id = _generated_opportunity(session)
    detail = get_opportunity_detail(session, opportunity_id)
    component_id = detail.components[0].id

    with pytest.raises(ValueError, match="actor"):
        review_opportunity(
            session,
            opportunity_id,
            ReviewAction.QUALIFY,
            actor=" ",
            now=NOW,
        )
    with pytest.raises(ValueError, match="at least one"):
        override_score_component(
            session,
            opportunity_id,
            component_id,
            actor="analyst",
            now=NOW,
        )
    with pytest.raises(ValueError, match="reason cannot be empty"):
        override_score_component(
            session,
            opportunity_id,
            component_id,
            actor="analyst",
            now=NOW,
            reason=" ",
        )

    session.rollback()
    assert session.scalar(select(func.count()).select_from(OpportunityReviewRecord)) == 0


def test_list_validation_and_empty_evaluation(session: Session) -> None:
    organization_id, _ = _seed_context(session)

    assert generate_siem_soc_opportunity(session, organization_id, now=NOW) is None
    with pytest.raises(ValueError, match="min_score"):
        list_opportunities(session, now=NOW, min_score=101)
    with pytest.raises(ValueError, match="pagination"):
        list_opportunities(session, now=NOW, limit=0)


def _generated_opportunity(session: Session) -> UUID:
    organization_id, evidence_ids = _seed_context(session)
    store_commercial_signal(
        session,
        _signal(
            organization_id,
            evidence_ids[0],
            SignalType.PUBLIC_TENDER,
            "SIEM tender",
        ),
    )
    opportunity_id = generate_siem_soc_opportunity(session, organization_id, now=NOW)
    assert opportunity_id is not None
    return opportunity_id


def _seed_context(session: Session) -> tuple[UUID, tuple[UUID, UUID]]:
    organization_id = uuid4()
    evidence_ids = (uuid4(), uuid4())
    session.add(
        OrganizationRecord(
            id=organization_id,
            canonical_name="Example Industries",
            legal_name="Example Industries SAS",
            country_code="FR",
            website_url="https://example.test",
            registration_ids=["SIREN:123456789"],
            created_at=NOW,
            updated_at=NOW,
        )
    )
    session.add_all(
        EvidenceRecord(
            id=evidence_id,
            source_id=f"source-{index}",
            source_record_key=f"record-{index}",
            source_url=f"https://source-{index}.example/item",
            summary="Public commercial signal",
            confidence=0.9,
            collected_at=NOW,
            published_at=NOW - timedelta(hours=index),
            observed_at=None,
            content_hash_sha256=None,
            raw_storage_uri=None,
            raw_storage_permitted=False,
            retention_until=NOW + timedelta(days=365),
        )
        for index, evidence_id in enumerate(evidence_ids, start=1)
    )
    session.flush()
    return organization_id, evidence_ids


def _signal(
    organization_id: UUID,
    evidence_id: UUID,
    signal_type: SignalType,
    title: str,
    *,
    confidence: float = 0.8,
) -> CommercialSignal:
    return CommercialSignal(
        organization_id=organization_id,
        evidence_id=evidence_id,
        signal_type=signal_type,
        title=title,
        summary=title,
        confidence=confidence,
        matched_terms=("siem", "soc"),
        published_at=NOW - timedelta(minutes=30),
        collected_at=NOW,
        expires_at=NOW + timedelta(days=90),
    )

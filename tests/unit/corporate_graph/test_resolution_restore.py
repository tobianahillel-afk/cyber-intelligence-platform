from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from cip.modules.corporate_graph.domain.models import GraphNodeSnapshot, GraphNodeType
from cip.modules.corporate_graph.domain.resolution import (
    EntityResolutionCandidate,
    ResolutionDecision,
    ResolutionDecisionType,
    ResolutionMethod,
)
from cip.modules.corporate_graph.infrastructure.blast_radius_queries import (
    build_blast_radius_preview,
)
from cip.modules.corporate_graph.infrastructure.models import (
    EntityResolutionBindingRecord,
    EntityResolutionDecisionRecord,
)
from cip.modules.corporate_graph.infrastructure.projections import persist_graph_nodes
from cip.modules.corporate_graph.infrastructure.resolution_persistence import (
    persist_resolution_candidate,
    record_resolution_decision,
)
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 8, 21, 0, tzinfo=UTC)


def test_merge_split_restore_keeps_append_only_decision_history() -> None:
    session = _session()
    organization = OrganizationRecord(
        id=uuid4(),
        canonical_name="Restore Corp",
        legal_name="Restore Corp",
        country_code="FR",
        website_url="https://restore.example",
        registration_ids=[],
        created_at=NOW,
        updated_at=NOW,
    )
    session.add(organization)
    session.flush()
    persist_graph_nodes(
        session,
        (
            GraphNodeSnapshot(
                node_key="brand:restore",
                node_type=GraphNodeType.BRAND,
                display_name="Restore",
                source_module="test",
                source_entity_type="brand",
                source_record_key="brand:restore",
                observed_at=NOW,
                confidence=0.7,
            ),
        ),
        now=NOW,
    )
    candidate = persist_resolution_candidate(
        session,
        EntityResolutionCandidate(
            node_key="brand:restore",
            candidate_organization_id=organization.id,
            method=ResolutionMethod.PROBABILISTIC_CONTEXT,
            score=0.7,
            reasons=("reviewed context",),
            created_at=NOW,
        ),
        now=NOW,
    )

    merge_preview = build_blast_radius_preview(
        session,
        node_key="brand:restore",
        organization_id=organization.id,
    )
    merge = _decision(
        candidate_id=candidate.id,
        decision_type=ResolutionDecisionType.MERGE,
        organization_id=organization.id,
        reverses_decision_id=None,
        fingerprint=merge_preview.fingerprint,
    )
    record_resolution_decision(session, merge, preview=merge_preview, now=NOW)

    split_preview = build_blast_radius_preview(
        session,
        node_key="brand:restore",
        organization_id=organization.id,
    )
    split = _decision(
        candidate_id=candidate.id,
        decision_type=ResolutionDecisionType.SPLIT,
        organization_id=None,
        reverses_decision_id=merge.decision_id,
        fingerprint=split_preview.fingerprint,
    )
    record_resolution_decision(session, split, preview=split_preview, now=NOW)

    restore_preview = build_blast_radius_preview(
        session,
        node_key="brand:restore",
        organization_id=organization.id,
    )
    restore = _decision(
        candidate_id=candidate.id,
        decision_type=ResolutionDecisionType.RESTORE,
        organization_id=organization.id,
        reverses_decision_id=split.decision_id,
        fingerprint=restore_preview.fingerprint,
    )
    record_resolution_decision(session, restore, preview=restore_preview, now=NOW)

    binding = session.scalar(
        select(EntityResolutionBindingRecord).where(
            EntityResolutionBindingRecord.node_key == "brand:restore"
        )
    )
    decisions = tuple(
        session.scalars(
            select(EntityResolutionDecisionRecord).order_by(
                EntityResolutionDecisionRecord.created_at,
                EntityResolutionDecisionRecord.id,
            )
        )
    )

    assert binding is not None
    assert binding.current is True
    assert binding.organization_id == organization.id
    assert binding.decision_id == restore.decision_id
    assert {item.decision_type for item in decisions} == {"merge", "split", "restore"}
    assert len(decisions) == 3


def _decision(
    *,
    candidate_id,
    decision_type: ResolutionDecisionType,
    organization_id,
    reverses_decision_id,
    fingerprint: str,
) -> ResolutionDecision:
    return ResolutionDecision.create(
        candidate_id=candidate_id,
        node_key="brand:restore",
        decision_type=decision_type,
        actor="analyst@example.test",
        reason=f"reviewed {decision_type.value}",
        organization_id=organization_id,
        reverses_decision_id=reverses_decision_id,
        blast_radius_fingerprint=fingerprint,
        decided_at=NOW,
    )


def _session():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return create_session_factory(engine)()

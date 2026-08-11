from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cip.modules.need_detection.domain.models import (
    EvidenceContribution,
    EvidencePosition,
    NeedHorizon,
    NeedHypothesisClass,
    NeedUrgency,
)

NOW = datetime(2026, 8, 11, 16, 30, tzinfo=UTC)


def test_need_taxonomy_contains_all_canonical_hypothesis_classes() -> None:
    assert {item.value for item in NeedHypothesisClass} == {
        "explicit_procurement",
        "contract_renewal_or_replacement",
        "program_build_or_transformation",
        "capability_gap",
        "incident_urgency",
        "regulatory_deadline_or_gap",
        "technology_risk_or_lifecycle",
        "external_exposure",
        "organizational_change",
        "provider_dissatisfaction_or_transition",
        "skills_and_training_need",
        "research_only_weak_signal",
    }
    assert {item.value for item in EvidencePosition} == {
        "supporting",
        "conflicting",
        "negative",
    }
    assert NeedUrgency.RESEARCH.value == "research"
    assert NeedHorizon.UNKNOWN.value == "unknown"


def test_evidence_contribution_preserves_explicit_independence_group() -> None:
    evidence_id = uuid4()
    signal_id = uuid4()
    contribution = EvidenceContribution(
        evidence_id=evidence_id,
        signal_id=signal_id,
        source_id="official-procurement",
        corroboration_group_key="contract:2026-42",
        position=EvidencePosition.SUPPORTING,
        confidence=0.9,
        effective_at=NOW,
        expires_at=NOW + timedelta(days=30),
        source_record_key="42",
        content_hash_sha256="a" * 64,
    )

    assert contribution.independence_key == "contract:2026-42"
    assert contribution.is_current_at(NOW + timedelta(days=29)) is True
    assert contribution.is_current_at(NOW + timedelta(days=30)) is False


def test_evidence_contribution_rejects_invalid_provenance() -> None:
    with pytest.raises(ValueError, match="source_id is required"):
        EvidenceContribution(
            evidence_id=uuid4(),
            source_id=" ",
            corroboration_group_key="group",
            position=EvidencePosition.SUPPORTING,
            confidence=0.8,
            effective_at=NOW,
        )

    with pytest.raises(ValueError, match="lowercase SHA-256"):
        EvidenceContribution(
            evidence_id=uuid4(),
            source_id="source",
            corroboration_group_key="group",
            position=EvidencePosition.SUPPORTING,
            confidence=0.8,
            effective_at=NOW,
            content_hash_sha256="NOT-A-HASH",
        )

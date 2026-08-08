from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from cip.modules.corporate_graph.domain.blast_radius import BlastRadiusPreview
from cip.modules.corporate_graph.domain.resolution import (
    EntityResolutionCandidate,
    ResolutionCandidateState,
    ResolutionDecision,
    ResolutionDecisionType,
    ResolutionMethod,
    can_auto_confirm,
)

NOW = datetime(2026, 8, 8, 20, 0, tzinfo=UTC)


def test_only_exact_methods_can_auto_confirm() -> None:
    assert can_auto_confirm(ResolutionMethod.EXACT_IDENTIFIER)
    assert can_auto_confirm(ResolutionMethod.EXACT_SOURCE_BINDING)
    assert not can_auto_confirm(ResolutionMethod.PROBABILISTIC_NAME_ADDRESS)


def test_conflict_disables_automatic_confirmation() -> None:
    conflict = uuid4()

    assert not can_auto_confirm(
        ResolutionMethod.EXACT_IDENTIFIER,
        conflicts=(conflict,),
    )


def test_probabilistic_candidate_requires_review() -> None:
    candidate = EntityResolutionCandidate(
        node_key="brand:acme",
        candidate_organization_id=uuid4(),
        method=ResolutionMethod.PROBABILISTIC_NAME_ADDRESS,
        score=0.98,
        reasons=("normalized name and address similarity",),
        created_at=NOW,
    )

    assert candidate.requires_review
    assert candidate.state is ResolutionCandidateState.PENDING


def test_invalid_auto_confirmation_is_rejected() -> None:
    with pytest.raises(ValueError, match="not eligible"):
        EntityResolutionCandidate(
            node_key="brand:acme",
            candidate_organization_id=uuid4(),
            method=ResolutionMethod.PROBABILISTIC_CONTEXT,
            score=0.99,
            reasons=("context similarity",),
            created_at=NOW,
            state=ResolutionCandidateState.AUTO_CONFIRMED,
        )


def test_resolution_decision_requires_blast_radius_preview() -> None:
    with pytest.raises(ValueError, match="blast-radius"):
        ResolutionDecision(
            candidate_id=uuid4(),
            node_key="brand:acme",
            decision_type=ResolutionDecisionType.MERGE,
            actor="analyst@example.test",
            reason="reviewed exact registry evidence",
            decided_at=NOW,
            organization_id=uuid4(),
        )


def test_split_and_restore_reference_prior_decision() -> None:
    preview = BlastRadiusPreview(
        node_key="brand:acme",
        target_organization_key="organization:acme",
        graph_edges=2,
    )
    with pytest.raises(ValueError, match="prior decision"):
        ResolutionDecision(
            candidate_id=uuid4(),
            node_key="brand:acme",
            decision_type=ResolutionDecisionType.SPLIT,
            actor="analyst@example.test",
            reason="incorrect historical merge",
            decided_at=NOW,
            blast_radius_fingerprint=preview.fingerprint,
        )


def test_blast_radius_fingerprint_changes_with_downstream_impact() -> None:
    base = BlastRadiusPreview(
        node_key="brand:acme",
        target_organization_key="organization:acme",
        graph_edges=2,
    )
    changed = BlastRadiusPreview(
        node_key="brand:acme",
        target_organization_key="organization:acme",
        graph_edges=2,
        opportunities=1,
    )

    assert base.fingerprint != changed.fingerprint
    assert changed.requires_explicit_confirmation

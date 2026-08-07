from __future__ import annotations

from dataclasses import dataclass

from cip.modules.relationship_intelligence.domain.models import (
    RelationshipContext,
    RelationshipEvidenceSnapshot,
)


@dataclass(frozen=True, slots=True)
class RelationshipProjectionBundle:
    evidence: tuple[RelationshipEvidenceSnapshot, ...]
    contexts: tuple[RelationshipContext, ...]

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SourceContributionView:
    independence_key: str
    polarity: str
    signal_ids: tuple[UUID, ...]
    max_confidence: float
    contribution: float


@dataclass(frozen=True, slots=True)
class NeedHypothesisView:
    id: UUID
    organization_id: UUID
    organization: str
    family: str
    status: str
    hypothesis_class: str
    service_families: tuple[str, ...]
    confidence: float
    urgency: str
    horizon: str
    rationale: str
    applicable_offers: tuple[str, ...]
    signal_ids: tuple[UUID, ...]
    evidence_ids: tuple[UUID, ...]
    conflicting_signal_ids: tuple[UUID, ...]
    negative_signal_ids: tuple[UUID, ...]
    source_contributions: tuple[SourceContributionView, ...]
    rule_id: str
    rule_version: str
    taxonomy_version: str
    generated_at: datetime
    expires_at: datetime

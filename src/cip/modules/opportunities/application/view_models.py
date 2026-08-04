from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class OpportunityListItem:
    id: UUID
    organization_id: UUID
    organization: str
    country: str | None
    family: str
    state: str
    data_quality: str
    recommended_offer: str
    score: float
    confidence: float
    trigger: str
    last_evidence_at: datetime
    updated_at: datetime
    relevant_roles: tuple[str, ...]
    next_action: str
    evidence_count: int
    snoozed_until: datetime | None


@dataclass(frozen=True, slots=True)
class OpportunityPage:
    items: tuple[OpportunityListItem, ...]
    total: int
    limit: int
    offset: int
    generated_at: datetime


@dataclass(frozen=True, slots=True)
class OpportunityEvidenceItem:
    id: UUID
    source_id: str
    source_url: str
    source_record_key: str | None
    summary: str
    confidence: float
    collected_at: datetime
    published_at: datetime | None
    observed_at: datetime | None


@dataclass(frozen=True, slots=True)
class OpportunityScoreComponentItem:
    id: UUID
    rule_id: str
    value: float
    weight: float
    contribution: float
    kind: str
    reason: str
    evidence_ids: tuple[UUID, ...]
    analyst_overridden: bool
    original_value: float | None
    original_weight: float | None


@dataclass(frozen=True, slots=True)
class OpportunityReviewItem:
    id: UUID
    action: str
    previous_state: str
    new_state: str
    actor: str
    note: str | None
    occurred_at: datetime
    snoozed_until: datetime | None


@dataclass(frozen=True, slots=True)
class OpportunityDetail:
    opportunity: OpportunityListItem
    hypothesis_id: UUID
    hypothesis_status: str
    rule_id: str
    rule_version: str
    rationale: str
    generated_at: datetime
    expires_at: datetime | None
    score_version: str
    config_version: str
    raw_score: float
    calculation_hash: str
    review_note: str | None
    rejected_reason: str | None
    components: tuple[OpportunityScoreComponentItem, ...]
    evidence: tuple[OpportunityEvidenceItem, ...]
    reviews: tuple[OpportunityReviewItem, ...]

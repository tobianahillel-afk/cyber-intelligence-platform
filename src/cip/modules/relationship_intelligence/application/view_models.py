from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RelationshipFilters:
    status: str | None = None
    role: str | None = None
    evidence_class: str | None = None
    source_kind: str | None = None
    source_link_status: str | None = None
    target_link_status: str | None = None
    organization_id: UUID | None = None
    contract_backed_current: bool | None = None
    historical_only: bool | None = None
    query: str | None = None


@dataclass(frozen=True, slots=True)
class RelationshipSummary:
    id: UUID
    relationship_key: str
    role: str
    status: str
    source_organization_id: UUID | None
    target_organization_id: UUID | None
    source_link_status: str
    target_link_status: str
    source_name: str | None
    target_name: str | None
    valid_from: datetime | None
    valid_until: datetime | None
    first_published_at: datetime
    last_updated_at: datetime
    last_observed_at: datetime
    evidence_count: int
    independent_source_count: int
    strongest_evidence_class: str
    confidence: float
    has_contract_evidence: bool
    contract_backed_current: bool
    next_renewal_at: datetime | None
    has_role_conflict: bool
    has_dispute: bool
    has_correction: bool
    has_retraction: bool
    historical_only: bool


@dataclass(frozen=True, slots=True)
class RelationshipPage:
    items: tuple[RelationshipSummary, ...]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class RelationshipEvidenceView:
    id: UUID
    source_id: str
    source_kind: str
    source_record_key: str
    source_url: str
    claim_type: str
    role: str
    evidence_class: str
    title: str
    excerpt: str
    claimed_source_organization_name: str | None
    claimed_target_organization_name: str | None
    source_organization_id: UUID | None
    target_organization_id: UUID | None
    source_link_status: str
    target_link_status: str
    published_at: datetime
    modified_at: datetime
    observed_at: datetime
    valid_from: datetime | None
    valid_until: datetime | None
    expires_at: datetime | None
    contract_reference: str | None
    product_context: str | None
    service_context: str | None
    renewal_at: datetime | None
    independence_key: str
    confidence: float
    active: bool
    historical_only: bool
    supersedes_record_key: str | None


@dataclass(frozen=True, slots=True)
class RelationshipContextView:
    id: UUID
    context_type: str
    value: str
    reference: str | None
    confidence: float
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RelationshipDetail:
    relationship: RelationshipSummary
    claimed_source_organization_names: tuple[str, ...]
    claimed_target_organization_names: tuple[str, ...]
    evidence: tuple[RelationshipEvidenceView, ...]
    contexts: tuple[RelationshipContextView, ...]

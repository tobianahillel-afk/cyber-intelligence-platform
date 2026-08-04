from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from cip.modules.organizations.domain.identity import (
    IdentityKind,
    IdentityStatus,
    MatchMethod,
    MatchState,
    RelationshipType,
)
from cip.modules.organizations.domain.identifiers import IdentifierScheme


@dataclass(frozen=True, slots=True)
class IdentifierView:
    scheme: IdentifierScheme
    value: str
    issuing_country: str | None
    source_id: str
    verified_at: datetime
    is_current: bool


@dataclass(frozen=True, slots=True)
class AliasView:
    value: str
    source_id: str
    observed_at: datetime


@dataclass(frozen=True, slots=True)
class RelationshipView:
    id: UUID
    subject_identity_id: UUID
    object_identity_id: UUID
    relationship_type: RelationshipType
    source_id: str
    source_url: str
    confidence: float
    observed_at: datetime
    valid_from: date | None
    valid_until: date | None


@dataclass(frozen=True, slots=True)
class IdentityView:
    id: UUID
    organization_id: UUID | None
    kind: IdentityKind
    official_name: str
    country_code: str
    status: IdentityStatus
    legal_form: str | None
    activity_code: str | None
    address: str | None
    postal_code: str | None
    city: str | None
    is_headquarters: bool
    source_id: str
    source_record_key: str
    source_url: str
    confidence: float
    observed_at: datetime
    valid_from: date | None
    valid_until: date | None
    identifiers: tuple[IdentifierView, ...]
    aliases: tuple[AliasView, ...]
    evidence_ids: tuple[UUID, ...]
    relationships: tuple[RelationshipView, ...]


@dataclass(frozen=True, slots=True)
class MergeCandidateView:
    id: UUID
    identity_id: UUID
    organization_id: UUID
    organization_name: str
    identity_name: str
    method: MatchMethod
    score: float
    reasons: tuple[str, ...]
    state: MatchState
    created_at: datetime
    reviewed_at: datetime | None
    reviewed_by: str | None
    review_note: str | None


@dataclass(frozen=True, slots=True)
class MergeCandidatePage:
    items: tuple[MergeCandidateView, ...]
    total: int
    limit: int
    offset: int

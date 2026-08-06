from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class IndicatorFilters:
    indicator_type: str | None = None
    state: str | None = None
    source_kind: str | None = None
    sensor_scope: str | None = None
    active: bool | None = None
    shared_infrastructure: bool | None = None
    historical_only: bool | None = None
    has_conflict: bool | None = None
    query: str | None = None


@dataclass(frozen=True, slots=True)
class IndicatorSummary:
    id: UUID
    indicator_key: str
    indicator_type: str
    indicator_value: str
    state: str
    observed_states: tuple[str, ...]
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    expires_at: datetime | None
    last_updated_at: datetime
    source_count: int
    independent_source_count: int
    active: bool
    shared_infrastructure: bool
    historical_only: bool
    has_conflict: bool


@dataclass(frozen=True, slots=True)
class IndicatorPage:
    items: tuple[IndicatorSummary, ...]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class IndicatorRelationView:
    relation_type: str
    target_key: str
    confidence: float


@dataclass(frozen=True, slots=True)
class IndicatorSnapshotView:
    id: UUID
    source_id: str
    source_kind: str
    source_record_key: str
    source_url: str
    state: str
    published_at: datetime
    modified_at: datetime
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    expires_at: datetime | None
    independence_key: str
    sensor_scope: str
    confidence: float
    source_precedence: int
    active: bool
    shared_infrastructure: bool
    historical_only: bool
    metadata_only: bool
    supersedes_record_key: str | None
    relations: tuple[IndicatorRelationView, ...]


@dataclass(frozen=True, slots=True)
class IndicatorDetail:
    indicator: IndicatorSummary
    snapshots: tuple[IndicatorSnapshotView, ...]
    safety_disclaimer: str = (
        "Global technical telemetry does not prove that a named organization is "
        "compromised or exposed. No direct malicious-host validation or binary "
        "collection is performed."
    )

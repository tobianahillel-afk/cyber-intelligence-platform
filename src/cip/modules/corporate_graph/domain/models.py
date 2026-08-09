from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlparse
from uuid import UUID

from cip.shared.kernel.time import require_aware_utc


class GraphNodeType(StrEnum):
    ORGANIZATION = "organization"
    ESTABLISHMENT = "establishment"
    GROUP = "group"
    BRAND = "brand"
    ALIAS = "alias"
    IDENTIFIER = "identifier"
    DOMAIN = "domain"
    ASSET = "asset"
    TECHNOLOGY = "technology"
    PRODUCT = "product"
    INCIDENT = "incident"
    VULNERABILITY = "vulnerability"
    PROVIDER = "provider"
    MATERIAL_CHANGE = "material_change"


class GraphEdgeType(StrEnum):
    IDENTITY_OF = "identity_of"
    ALIAS_OF = "alias_of"
    IDENTIFIES = "identifies"
    ESTABLISHMENT_OF = "establishment_of"
    BRAND_OF = "brand_of"
    PARENT_OF = "parent_of"
    SUBSIDIARY_OF = "subsidiary_of"
    PREDECESSOR_OF = "predecessor_of"
    SUCCESSOR_OF = "successor_of"
    MERGED_INTO = "merged_into"
    SPIN_OFF_OF = "spin_off_of"
    USES_DOMAIN = "uses_domain"
    OWNS_ASSET = "owns_asset"
    USES_TECHNOLOGY = "uses_technology"
    USES_PRODUCT = "uses_product"
    INCIDENT_INVOLVES = "incident_involves"
    VULNERABILITY_APPLIES_TO = "vulnerability_applies_to"
    MATERIAL_CHANGE_AFFECTS = "material_change_affects"
    PROVIDES_TO = "provides_to"
    CUSTOMER_OF = "customer_of"
    PARTNER_OF = "partner_of"
    SUPPLIES_TO = "supplies_to"
    RESELLS_TO = "resells_to"
    DISTRIBUTES_TO = "distributes_to"
    INTEGRATES_FOR = "integrates_for"
    AUDITS = "audits"
    INSURES = "insures"
    SECURES = "secures"
    HOSTS_FOR = "hosts_for"
    SUBCONTRACTS_FOR = "subcontracts_for"
    RELATED_TO = "related_to"


class GraphClaimType(StrEnum):
    ASSERTION = "assertion"
    DISPUTE = "dispute"
    CORRECTION = "correction"
    RETRACTION = "retraction"


class GraphReviewState(StrEnum):
    UNREVIEWED = "unreviewed"
    AUTO_CONFIRMED = "auto_confirmed"
    REVIEW_REQUIRED = "review_required"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class GraphNodeSnapshot:
    node_key: str
    node_type: GraphNodeType
    display_name: str
    source_module: str
    source_entity_type: str
    source_record_key: str
    observed_at: datetime
    confidence: float
    source_entity_id: UUID | None = None
    organization_id: UUID | None = None
    source_url: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    active: bool = True
    suppressed: bool = False
    metadata_only: bool = True

    def __post_init__(self) -> None:
        _required(self.node_key, "node_key", 500)
        _required(self.display_name, "display_name", 500)
        _required(self.source_module, "source_module", 100)
        _required(self.source_entity_type, "source_entity_type", 100)
        _required(self.source_record_key, "source_record_key", 500)
        _validate_confidence(self.confidence)
        _validate_source_url(self.source_url)
        _normalize_times(self, ("observed_at", "valid_from", "valid_until"))
        _validate_validity(self.valid_from, self.valid_until)
        if not self.metadata_only:
            raise ValueError("corporate graph accepts metadata projections only")

    def is_current_at(self, now: datetime) -> bool:
        current = require_aware_utc(now, field_name="now")
        if not self.active or self.suppressed:
            return False
        if self.valid_from is not None and self.valid_from > current:
            return False
        return self.valid_until is None or self.valid_until > current


@dataclass(frozen=True, slots=True)
class GraphEdgeSnapshot:
    edge_key: str
    source_node_key: str
    target_node_key: str
    edge_type: GraphEdgeType
    source_module: str
    source_record_key: str
    source_evidence_class: str
    claim_type: GraphClaimType
    review_state: GraphReviewState
    observed_at: datetime
    confidence: float
    source_url: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    expires_at: datetime | None = None
    active: bool = True
    suppressed: bool = False
    supersedes_record_key: str | None = None

    def __post_init__(self) -> None:
        _required(self.edge_key, "edge_key", 500)
        _required(self.source_node_key, "source_node_key", 500)
        _required(self.target_node_key, "target_node_key", 500)
        if self.source_node_key == self.target_node_key:
            raise ValueError("graph edge cannot be self-referential")
        _required(self.source_module, "source_module", 100)
        _required(self.source_record_key, "source_record_key", 500)
        _required(self.source_evidence_class, "source_evidence_class", 100)
        _optional(self.supersedes_record_key, "supersedes_record_key", 500)
        _validate_confidence(self.confidence)
        _validate_source_url(self.source_url)
        _normalize_times(
            self,
            ("observed_at", "valid_from", "valid_until", "expires_at"),
        )
        _validate_validity(self.valid_from, self.valid_until)

    def is_current_at(self, now: datetime) -> bool:
        current = require_aware_utc(now, field_name="now")
        if not self.active or self.suppressed:
            return False
        if self.claim_type in {GraphClaimType.RETRACTION, GraphClaimType.DISPUTE}:
            return False
        if self.review_state is GraphReviewState.REJECTED:
            return False
        if self.valid_from is not None and self.valid_from > current:
            return False
        if self.valid_until is not None and self.valid_until <= current:
            return False
        return self.expires_at is None or self.expires_at > current

    @property
    def preserves_weak_evidence(self) -> bool:
        return self.source_evidence_class.casefold() in {
            "claimed",
            "historical",
            "inferred",
            "alleged",
            "reported",
            "speculative",
        }


@dataclass(frozen=True, slots=True)
class GraphNodeProjection:
    node_key: str
    node_type: GraphNodeType
    display_name: str
    organization_id: UUID | None
    source_count: int
    confidence: float
    current: bool
    suppressed: bool
    first_observed_at: datetime
    last_observed_at: datetime


@dataclass(frozen=True, slots=True)
class GraphEdgeProjection:
    edge_key: str
    source_node_key: str
    target_node_key: str
    edge_type: GraphEdgeType
    source_module: str
    source_evidence_class: str
    review_state: GraphReviewState
    confidence: float
    current: bool
    suppressed: bool
    valid_from: datetime | None
    valid_until: datetime | None
    first_observed_at: datetime
    last_observed_at: datetime


def _normalize_times(instance: object, fields: tuple[str, ...]) -> None:
    for field_name in fields:
        value = getattr(instance, field_name)
        if value is not None:
            object.__setattr__(
                instance,
                field_name,
                require_aware_utc(value, field_name=field_name),
            )


def _validate_validity(start: datetime | None, end: datetime | None) -> None:
    if start is not None and end is not None and end < start:
        raise ValueError("valid_until cannot precede valid_from")


def _validate_confidence(value: float) -> None:
    if not 0 <= value <= 1:
        raise ValueError("confidence must be between 0 and 1")


def _validate_source_url(value: str | None) -> None:
    if value is None:
        return
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source_url must use http or https")


def _required(value: str, name: str, maximum: int) -> None:
    if not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must be between 1 and {maximum} characters")


def _optional(value: str | None, name: str, maximum: int) -> None:
    if value is not None:
        _required(value, name, maximum)

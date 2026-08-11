from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from uuid import UUID, uuid4

from cip.modules.service_taxonomy.domain.models import (
    SERVICE_TAXONOMY_VERSION,
    CyberServiceFamily,
)
from cip.shared.kernel.time import require_aware_utc, utc_now


class SignalType(StrEnum):
    PUBLIC_TENDER = "public_tender"
    JOB_POSTING = "job_posting"
    CONTRACT_LIFECYCLE = "contract_lifecycle"
    REGULATORY_CHANGE = "regulatory_change"
    INCIDENT = "incident"
    VULNERABILITY_APPLICABILITY = "vulnerability_applicability"
    PASSIVE_EXPOSURE = "passive_exposure"
    TECHNOLOGY_CHANGE = "technology_change"
    CORPORATE_CHANGE = "corporate_change"
    RELATIONSHIP = "relationship"
    PROFESSIONAL_CONTEXT = "professional_context"
    RESEARCH_DISCOVERY = "research_discovery"


class SignalPolarity(StrEnum):
    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    NEGATIVE = "negative"


class NeedHypothesisClass(StrEnum):
    EXPLICIT_PROCUREMENT = "explicit_procurement"
    CONTRACT_RENEWAL_REPLACEMENT = "contract_renewal_or_replacement"
    CONTRACT_RENEWAL_OR_REPLACEMENT = "contract_renewal_or_replacement"
    PROGRAM_BUILD_TRANSFORMATION = "program_build_or_transformation"
    PROGRAM_BUILD_OR_TRANSFORMATION = "program_build_or_transformation"
    CAPABILITY_GAP = "capability_gap"
    INCIDENT_URGENCY = "incident_urgency"
    REGULATORY_DEADLINE_GAP = "regulatory_deadline_or_gap"
    REGULATORY_DEADLINE_OR_GAP = "regulatory_deadline_or_gap"
    TECHNOLOGY_RISK_LIFECYCLE = "technology_risk_or_lifecycle"
    TECHNOLOGY_RISK_OR_LIFECYCLE = "technology_risk_or_lifecycle"
    EXTERNAL_EXPOSURE = "external_exposure"
    ORGANIZATIONAL_CHANGE = "organizational_change"
    PROVIDER_DISSATISFACTION_TRANSITION = "provider_dissatisfaction_or_transition"
    PROVIDER_DISSATISFACTION_OR_TRANSITION = "provider_dissatisfaction_or_transition"
    SKILLS_TRAINING = "skills_and_training_need"
    SKILLS_AND_TRAINING_NEED = "skills_and_training_need"
    RESEARCH_ONLY_WEAK_SIGNAL = "research_only_weak_signal"


class NeedUrgency(StrEnum):
    IMMEDIATE = "immediate"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class NeedHorizon(StrEnum):
    IMMEDIATE = "immediate"
    NEAR_TERM = "near_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


class OpportunityFamily(StrEnum):
    SIEM_SOC_BUYING_INTENT = "siem_soc_buying_intent"
    CYBER_SERVICE_NEED = "cyber_service_need"


class HypothesisStatus(StrEnum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    DISMISSED = "dismissed"


@dataclass(frozen=True, slots=True)
class SourceContribution:
    independence_key: str
    polarity: SignalPolarity
    signal_ids: tuple[UUID, ...]
    max_confidence: float
    contribution: float

    def __post_init__(self) -> None:
        key = self.independence_key.strip()
        if not key:
            raise ValueError("independence_key is required")
        signal_ids = tuple(dict.fromkeys(self.signal_ids))
        if not signal_ids:
            raise ValueError("source contribution requires signal_ids")
        if not 0.0 <= self.max_confidence <= 1.0:
            raise ValueError("max_confidence must be between 0 and 1")
        if not -1.0 <= self.contribution <= 1.0:
            raise ValueError("contribution must be between -1 and 1")
        object.__setattr__(self, "independence_key", key)
        object.__setattr__(self, "signal_ids", signal_ids)


@dataclass(frozen=True, slots=True)
class CommercialSignal:
    organization_id: UUID
    evidence_id: UUID
    signal_type: SignalType
    title: str
    summary: str
    confidence: float
    collected_at: datetime
    id: UUID = field(default_factory=uuid4)
    matched_terms: tuple[str, ...] = ()
    published_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    service_families: tuple[CyberServiceFamily, ...] = ()
    hypothesis_classes: tuple[NeedHypothesisClass, ...] = ()
    independence_key: str | None = None
    corroboration_group_key: str | None = None
    polarity: SignalPolarity = SignalPolarity.SUPPORTING
    is_explicit: bool = False
    historical_only: bool = False
    mapping_rule_id: str = "legacy-signal"
    mapping_rule_version: str = "1.0.0"

    def __post_init__(self) -> None:
        title = self.title.strip()
        summary = self.summary.strip()
        if not title:
            raise ValueError("title is required")
        if len(title) > 500:
            raise ValueError("title cannot exceed 500 characters")
        if not summary:
            raise ValueError("summary is required")
        if len(summary) > 4_000:
            raise ValueError("summary cannot exceed 4000 characters")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        rule_id = self.mapping_rule_id.strip()
        rule_version = self.mapping_rule_version.strip()
        if not rule_id or not rule_version:
            raise ValueError("mapping rule id and version are required")
        independence = (self.independence_key or f"evidence:{self.evidence_id}").strip()
        if not independence:
            raise ValueError("independence_key cannot be empty")
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "summary", summary)
        object.__setattr__(self, "matched_terms", _normalized_terms(self.matched_terms))
        object.__setattr__(self, "service_families", _unique_enum_values(self.service_families))
        object.__setattr__(
            self, "hypothesis_classes", _unique_enum_values(self.hypothesis_classes)
        )
        object.__setattr__(self, "independence_key", independence)
        object.__setattr__(
            self, "corroboration_group_key", _optional_text(self.corroboration_group_key)
        )
        object.__setattr__(self, "mapping_rule_id", rule_id)
        object.__setattr__(self, "mapping_rule_version", rule_version)
        for field_name in ("collected_at", "created_at"):
            object.__setattr__(
                self,
                field_name,
                require_aware_utc(getattr(self, field_name), field_name=field_name),
            )
        for field_name in ("published_at", "expires_at"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    require_aware_utc(value, field_name=field_name),
                )
        if self.expires_at is not None and self.expires_at <= self.collected_at:
            raise ValueError("expires_at must be later than collected_at")

    @property
    def idempotency_key(self) -> str:
        material = f"{self.organization_id}\0{self.evidence_id}\0{self.signal_type.value}"
        if self.mapping_rule_id != "legacy-signal" or self.mapping_rule_version != "1.0.0":
            material += f"\0{self.mapping_rule_id}\0{self.mapping_rule_version}"
        return sha256(material.encode("utf-8")).hexdigest()

    @property
    def effective_at(self) -> datetime:
        return self.published_at or self.collected_at

    @property
    def corroboration_key(self) -> str:
        return self.corroboration_group_key or self.independence_key or str(self.evidence_id)


@dataclass(frozen=True, slots=True)
class NeedHypothesis:
    organization_id: UUID
    family: OpportunityFamily
    rule_id: str
    rule_version: str
    rationale: str
    signal_ids: tuple[UUID, ...]
    evidence_ids: tuple[UUID, ...]
    generated_at: datetime
    expires_at: datetime
    id: UUID = field(default_factory=uuid4)
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    hypothesis_class: NeedHypothesisClass = NeedHypothesisClass.RESEARCH_ONLY_WEAK_SIGNAL
    service_families: tuple[CyberServiceFamily, ...] = ()
    confidence: float = 0.5
    urgency: NeedUrgency = NeedUrgency.LOW
    horizon: NeedHorizon = NeedHorizon.LONG_TERM
    applicable_offers: tuple[str, ...] = ()
    conflicting_signal_ids: tuple[UUID, ...] = ()
    negative_signal_ids: tuple[UUID, ...] = ()
    source_contributions: tuple[SourceContribution, ...] = ()
    taxonomy_version: str = SERVICE_TAXONOMY_VERSION

    def __post_init__(self) -> None:
        rule_id = self.rule_id.strip()
        rule_version = self.rule_version.strip()
        rationale = self.rationale.strip()
        taxonomy_version = self.taxonomy_version.strip()
        if not rule_id or not rule_version:
            raise ValueError("rule_id and rule_version are required")
        if not rationale:
            raise ValueError("rationale is required")
        if not taxonomy_version:
            raise ValueError("taxonomy_version is required")
        if not self.signal_ids or not self.evidence_ids:
            raise ValueError("a hypothesis requires signals and evidence")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        generated_at = require_aware_utc(self.generated_at, field_name="generated_at")
        expires_at = require_aware_utc(self.expires_at, field_name="expires_at")
        if expires_at <= generated_at:
            raise ValueError("expires_at must be later than generated_at")
        object.__setattr__(self, "rule_id", rule_id)
        object.__setattr__(self, "rule_version", rule_version)
        object.__setattr__(self, "rationale", rationale)
        object.__setattr__(self, "taxonomy_version", taxonomy_version)
        object.__setattr__(self, "generated_at", generated_at)
        object.__setattr__(self, "expires_at", expires_at)
        object.__setattr__(self, "signal_ids", _unique_ids(self.signal_ids))
        object.__setattr__(self, "evidence_ids", _unique_ids(self.evidence_ids))
        object.__setattr__(
            self, "conflicting_signal_ids", _unique_ids(self.conflicting_signal_ids)
        )
        object.__setattr__(self, "negative_signal_ids", _unique_ids(self.negative_signal_ids))
        object.__setattr__(self, "service_families", _unique_enum_values(self.service_families))
        offers = tuple(
            dict.fromkeys(value.strip() for value in self.applicable_offers if value.strip())
        )
        object.__setattr__(self, "applicable_offers", offers)
        contribution_keys = [item.independence_key for item in self.source_contributions]
        if len(contribution_keys) != len(set(contribution_keys)):
            raise ValueError("source contributions require unique independence keys")

    @property
    def idempotency_key(self) -> str:
        material = (
            f"{self.organization_id}\0{self.family.value}\0"
            f"{self.rule_id}\0{self.rule_version}"
        )
        if self.service_families:
            services = ",".join(family.value for family in self.service_families)
            material += (
                f"\0{self.hypothesis_class.value}\0{services}\0{self.taxonomy_version}"
            )
        return sha256(material.encode("utf-8")).hexdigest()

    @property
    def all_signal_ids(self) -> tuple[UUID, ...]:
        return _unique_ids(
            self.signal_ids + self.conflicting_signal_ids + self.negative_signal_ids
        )


def _normalized_terms(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(value.strip().casefold() for value in values if value.strip())
    )


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _unique_ids(values: tuple[UUID, ...]) -> tuple[UUID, ...]:
    return tuple(dict.fromkeys(values))


def _unique_enum_values[T: StrEnum](values: tuple[T, ...]) -> tuple[T, ...]:
    return tuple(dict.fromkeys(values))

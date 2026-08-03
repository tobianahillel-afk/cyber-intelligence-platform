from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from json import dumps
from uuid import UUID

from cip.shared.kernel.time import require_aware_utc, utc_now


class ComponentKind(StrEnum):
    POSITIVE = "positive"
    PENALTY = "penalty"


@dataclass(frozen=True, slots=True)
class OpportunityComponent:
    rule_id: str
    value: float
    weight: float
    reason: str
    kind: ComponentKind = ComponentKind.POSITIVE
    evidence_ids: tuple[UUID, ...] = ()

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise ValueError("rule_id is required")
        if not self.reason.strip():
            raise ValueError("reason is required")
        if not 0.0 <= self.value <= 1.0:
            raise ValueError("value must be between 0 and 1")
        if not 0.0 <= self.weight <= 100.0:
            raise ValueError("weight must be between 0 and 100")

    @property
    def contribution(self) -> float:
        magnitude = self.value * self.weight
        return magnitude if self.kind is ComponentKind.POSITIVE else -magnitude


@dataclass(frozen=True, slots=True)
class OpportunityScore:
    organization_id: UUID
    score_version: str
    config_version: str
    components: tuple[OpportunityComponent, ...]
    generated_at: datetime = field(default_factory=utc_now)
    expires_at: datetime | None = None
    raw_score: float = field(init=False)
    adjusted_score: float = field(init=False)
    calculation_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.score_version.strip() or not self.config_version.strip():
            raise ValueError("score_version and config_version are required")
        generated_at = require_aware_utc(self.generated_at, field_name="generated_at")
        object.__setattr__(self, "generated_at", generated_at)
        if self.expires_at is not None:
            expires_at = require_aware_utc(self.expires_at, field_name="expires_at")
            if expires_at <= generated_at:
                raise ValueError("expires_at must be later than generated_at")
            object.__setattr__(self, "expires_at", expires_at)
        raw_score = sum(component.contribution for component in self.components)
        adjusted_score = min(100.0, max(0.0, raw_score))
        object.__setattr__(self, "raw_score", round(raw_score, 6))
        object.__setattr__(self, "adjusted_score", round(adjusted_score, 6))
        object.__setattr__(self, "calculation_hash", self._build_hash())

    def _build_hash(self) -> str:
        payload = {
            "organization_id": str(self.organization_id),
            "score_version": self.score_version,
            "config_version": self.config_version,
            "components": [
                {
                    "rule_id": component.rule_id,
                    "value": component.value,
                    "weight": component.weight,
                    "kind": component.kind.value,
                    "evidence_ids": sorted(str(value) for value in component.evidence_ids),
                }
                for component in self.components
            ],
        }
        encoded = dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return sha256(encoded).hexdigest()

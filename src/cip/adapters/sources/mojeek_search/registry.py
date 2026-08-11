from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class _MojeekEntitlementModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    durable_storage_authorized: bool = False
    plan: str = Field(default="unprovisioned", min_length=1, max_length=100)
    evidence_reference: str | None = Field(default=None, max_length=1_000)


class _MojeekRegistryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    entitlement: _MojeekEntitlementModel


@dataclass(frozen=True, slots=True)
class MojeekSearchEntitlement:
    durable_storage_authorized: bool
    plan: str
    evidence_reference: str | None

    def __post_init__(self) -> None:
        normalized_plan = self.plan.strip()
        if not normalized_plan:
            raise ValueError("Mojeek plan is required")
        evidence = None if self.evidence_reference is None else self.evidence_reference.strip()
        if self.durable_storage_authorized and not evidence:
            raise ValueError(
                "durable Mojeek storage authorization requires an evidence reference"
            )
        object.__setattr__(self, "plan", normalized_plan)
        object.__setattr__(self, "evidence_reference", evidence or None)


def load_mojeek_search_entitlement(path: Path) -> MojeekSearchEntitlement:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    parsed = _MojeekRegistryModel.model_validate(payload)
    item = parsed.entitlement
    return MojeekSearchEntitlement(
        durable_storage_authorized=item.durable_storage_authorized,
        plan=item.plan,
        evidence_reference=item.evidence_reference,
    )

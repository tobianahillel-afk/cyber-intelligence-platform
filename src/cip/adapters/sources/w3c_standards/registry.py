from __future__ import annotations

from pathlib import Path
from uuid import UUID

import yaml
from pydantic import BaseModel, ConfigDict, Field


class W3cAffiliationTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    target_id: str = Field(min_length=1, max_length=200)
    organization_id: UUID
    canonical_name: str = Field(min_length=1, max_length=300)
    affiliation_id: int = Field(ge=1)
    enabled: bool = False


class W3cAffiliationTargetFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1, le=1)
    targets: list[W3cAffiliationTarget] = Field(default_factory=list, max_length=500)


def load_w3c_affiliation_targets(path: Path) -> tuple[W3cAffiliationTarget, ...]:
    parsed = W3cAffiliationTargetFile.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )
    targets = tuple(parsed.targets)
    target_ids = [target.target_id for target in targets]
    affiliation_ids = [target.affiliation_id for target in targets]
    if len(target_ids) != len(set(target_ids)):
        raise ValueError("duplicate W3C affiliation target_id")
    if len(affiliation_ids) != len(set(affiliation_ids)):
        raise ValueError("duplicate W3C affiliation_id")
    return targets

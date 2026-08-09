from __future__ import annotations

from pathlib import Path
from uuid import UUID

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from cip.modules.passive_exposure.domain.normalization import normalize_domain


class PassiveInfrastructureTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str = Field(min_length=1, max_length=200)
    organization_id: UUID
    domain: str = Field(min_length=1, max_length=253)
    enabled: bool = False

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        return normalize_domain(value)


class PassiveInfrastructureTargetFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1, le=1)
    targets: list[PassiveInfrastructureTarget] = Field(default_factory=list)


def load_passive_infrastructure_targets(
    path: Path,
) -> tuple[PassiveInfrastructureTarget, ...]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    parsed = PassiveInfrastructureTargetFile.model_validate(document)
    values = tuple(parsed.targets)
    target_ids = [target.target_id for target in values]
    if len(target_ids) != len(set(target_ids)):
        raise ValueError("duplicate passive infrastructure target_id")
    return values

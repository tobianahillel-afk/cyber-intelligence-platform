from __future__ import annotations

from pathlib import Path
from uuid import UUID

import yaml
from pydantic import BaseModel, ConfigDict, Field


class PatentsViewPatentTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    target_id: str = Field(min_length=1, max_length=200)
    organization_id: UUID
    canonical_name: str = Field(min_length=1, max_length=300)
    assignee_organization: str = Field(min_length=2, max_length=500)
    enabled: bool = False


class PatentsViewPatentTargetFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1, le=1)
    targets: list[PatentsViewPatentTarget] = Field(default_factory=list, max_length=500)


def load_patentsview_patent_targets(path: Path) -> tuple[PatentsViewPatentTarget, ...]:
    parsed = PatentsViewPatentTargetFile.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )
    targets = tuple(parsed.targets)
    ids = [target.target_id for target in targets]
    identities = [target.assignee_organization.casefold() for target in targets]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate PatentsView patent target_id")
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate PatentsView assignee target")
    return targets

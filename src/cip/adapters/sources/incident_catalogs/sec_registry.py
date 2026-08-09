from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

_CIK = re.compile(r"^[0-9]{10}$")


class SecIncidentTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str = Field(min_length=1, max_length=200)
    organization_id: UUID
    cik: str
    enabled: bool = False

    @field_validator("cik")
    @classmethod
    def validate_cik(cls, value: str) -> str:
        normalized = value.strip()
        if not _CIK.fullmatch(normalized):
            raise ValueError("SEC CIK must contain exactly 10 digits")
        return normalized


class SecIncidentTargetFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1, le=1)
    targets: list[SecIncidentTarget] = Field(default_factory=list, max_length=500)


def load_sec_incident_targets(path: Path) -> tuple[SecIncidentTarget, ...]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    parsed = SecIncidentTargetFile.model_validate(document)
    targets = tuple(parsed.targets)
    ids = [target.target_id for target in targets]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate SEC incident target_id")
    ciks = [target.cik for target in targets]
    if len(ciks) != len(set(ciks)):
        raise ValueError("duplicate SEC CIK target")
    return targets

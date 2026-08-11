from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

_ROR_PATTERN = re.compile(r"^[0-9a-z]{9}$")
_ROR_PREFIX = "https://ror.org/"


class CrossrefPublicationTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    target_id: str = Field(min_length=1, max_length=200)
    organization_id: UUID
    canonical_name: str = Field(min_length=1, max_length=300)
    ror_id: str = Field(min_length=9, max_length=30)
    enabled: bool = False

    @field_validator("ror_id")
    @classmethod
    def normalize_ror_id(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if normalized.startswith(_ROR_PREFIX):
            normalized = normalized.removeprefix(_ROR_PREFIX)
        if not _ROR_PATTERN.fullmatch(normalized):
            raise ValueError("ror_id must be a nine-character ROR identifier")
        return normalized


class CrossrefPublicationTargetFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1, le=1)
    targets: list[CrossrefPublicationTarget] = Field(default_factory=list, max_length=500)


def load_crossref_publication_targets(
    path: Path,
) -> tuple[CrossrefPublicationTarget, ...]:
    parsed = CrossrefPublicationTargetFile.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )
    targets = tuple(parsed.targets)
    ids = [target.target_id for target in targets]
    ror_ids = [target.ror_id for target in targets]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate Crossref publication target_id")
    if len(ror_ids) != len(set(ror_ids)):
        raise ValueError("duplicate Crossref publication ROR target")
    return targets

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from uuid import UUID

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cip.modules.professional_context.domain.enums import LawfulBasis

_USERNAME = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_SITE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._()+&'/-]{0,99}$")


class SherlockTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    target_id: str = Field(min_length=1, max_length=200)
    organization_id: UUID | None = None
    person_key: str | None = Field(default=None, min_length=1, max_length=200)
    username: str = Field(min_length=1, max_length=64)
    sites: tuple[str, ...] = Field(min_length=1, max_length=25)
    authorization_reference: str = Field(min_length=1, max_length=500)
    lawful_basis: LawfulBasis
    purpose: str = Field(min_length=1, max_length=300)
    reviewed_at: datetime
    retention_until: datetime
    enabled: bool = False

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not _USERNAME.fullmatch(value) or value in {".", ".."}:
            raise ValueError("Sherlock username must be a bounded filename-safe username")
        return value

    @field_validator("sites")
    @classmethod
    def validate_sites(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(site.strip() for site in value)
        if any(not _SITE.fullmatch(site) for site in normalized):
            raise ValueError("Sherlock sites must be bounded explicit site names")
        if len({site.casefold() for site in normalized}) != len(normalized):
            raise ValueError("Sherlock target contains duplicate site names")
        return normalized

    @model_validator(mode="after")
    def validate_governance(self) -> SherlockTarget:
        if (self.organization_id is None) == (self.person_key is None):
            raise ValueError("Sherlock target requires exactly one organization or person context")
        if self.reviewed_at.tzinfo is None or self.retention_until.tzinfo is None:
            raise ValueError("Sherlock governance timestamps must be timezone-aware")
        if self.retention_until <= self.reviewed_at:
            raise ValueError("Sherlock retention must extend beyond governance review")
        if self.enabled and self.lawful_basis is LawfulBasis.REVIEW_REQUIRED:
            raise ValueError("enabled Sherlock target requires a reviewed lawful basis")
        return self


class SherlockTargetFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1, le=1)
    targets: list[SherlockTarget] = Field(default_factory=list, max_length=100)


def load_sherlock_targets(path: Path) -> tuple[SherlockTarget, ...]:
    parsed = SherlockTargetFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    targets = tuple(parsed.targets)
    ids = [target.target_id for target in targets]
    identities = [
        (
            str(target.organization_id) if target.organization_id is not None else target.person_key,
            target.username.casefold(),
        )
        for target in targets
    ]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate Sherlock target_id")
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate Sherlock professional username target")
    return targets

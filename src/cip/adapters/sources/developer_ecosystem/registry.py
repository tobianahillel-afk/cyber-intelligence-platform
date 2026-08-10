from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from uuid import UUID

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class DeveloperTargetKind(StrEnum):
    GITHUB_ORG = "github_org"
    GITLAB_GROUP = "gitlab_group"
    PYPI_PACKAGE = "pypi_package"
    NPM_PACKAGE = "npm_package"
    MAVEN_ARTIFACT = "maven_artifact"


class DeveloperEcosystemTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    target_id: str = Field(min_length=1, max_length=200)
    organization_id: UUID
    kind: DeveloperTargetKind
    namespace: str | None = Field(default=None, min_length=1, max_length=300)
    name: str | None = Field(default=None, min_length=1, max_length=300)
    enabled: bool = False

    @model_validator(mode="after")
    def validate_identity(self) -> DeveloperEcosystemTarget:
        if self.kind in {DeveloperTargetKind.GITHUB_ORG, DeveloperTargetKind.GITLAB_GROUP}:
            if self.namespace is None or self.name is not None:
                raise ValueError("repository targets require namespace only")
        elif self.kind in {DeveloperTargetKind.PYPI_PACKAGE, DeveloperTargetKind.NPM_PACKAGE}:
            if self.name is None or self.namespace is not None:
                raise ValueError("package targets require name only")
        elif self.namespace is None or self.name is None:
            raise ValueError("Maven targets require group namespace and artifact name")
        return self

    @property
    def resource_identity(self) -> str:
        if self.kind is DeveloperTargetKind.MAVEN_ARTIFACT:
            return f"{self.namespace}:{self.name}"
        return self.namespace or self.name or ""


class DeveloperEcosystemTargetFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1, le=1)
    targets: list[DeveloperEcosystemTarget] = Field(default_factory=list, max_length=500)


def load_developer_ecosystem_targets(path: Path) -> tuple[DeveloperEcosystemTarget, ...]:
    parsed = DeveloperEcosystemTargetFile.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )
    targets = tuple(parsed.targets)
    ids = [target.target_id for target in targets]
    identities = [(target.kind, target.resource_identity.casefold()) for target in targets]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate developer ecosystem target_id")
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate developer ecosystem target resource")
    return targets

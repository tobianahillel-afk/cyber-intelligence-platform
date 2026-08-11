from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from cip.modules.public_footprint.domain.search import SearchQueryTemplate


class GitHubCodeSearchTemplateRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(min_length=1, max_length=100)
    version: int = Field(ge=1)
    query_pattern: str = Field(min_length=1, max_length=500)
    purpose: str = Field(min_length=1, max_length=200)
    enabled: bool = False

    @model_validator(mode="after")
    def validate_query(self) -> GitHubCodeSearchTemplateRecord:
        if self.query_pattern.count("{organization}") != 1:
            raise ValueError("GitHub code-search query requires one {organization} placeholder")
        if "org:{organization}" not in self.query_pattern:
            raise ValueError("GitHub code-search query must be organization-scoped")
        forbidden = ("password", "secret", "token", "credential", "private_key")
        if any(term in self.query_pattern.casefold() for term in forbidden):
            raise ValueError("GitHub code-search query may not hunt for secrets")
        return self

    def to_domain(self) -> SearchQueryTemplate:
        return SearchQueryTemplate(
            id=self.id,
            version=self.version,
            query_pattern=self.query_pattern,
            purpose=self.purpose,
            enabled=self.enabled,
        )


class GitHubCodeSearchTemplateFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1, le=1)
    templates: list[GitHubCodeSearchTemplateRecord] = Field(
        default_factory=list,
        max_length=50,
    )


def load_github_code_search_templates(path: Path) -> tuple[SearchQueryTemplate, ...]:
    parsed = GitHubCodeSearchTemplateFile.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )
    templates = tuple(record.to_domain() for record in parsed.templates)
    ids = [template.id for template in templates]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate GitHub code-search template id")
    return templates

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GitHubRepositoryRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=500)
    full_name: str = Field(min_length=1, max_length=1_000)
    html_url: str = Field(pattern=r"^https://github\.com/", max_length=2_048)
    description: str | None = Field(default=None, max_length=2_000)
    fork: bool = False
    archived: bool = False
    disabled: bool = False
    visibility: str = Field(default="public", max_length=30)
    language: str | None = Field(default=None, max_length=100)
    topics: list[str] = Field(default_factory=list, max_length=100)
    created_at: datetime
    updated_at: datetime
    pushed_at: datetime | None = None


class GitLabProjectRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=500)
    path_with_namespace: str = Field(min_length=1, max_length=1_000)
    web_url: str = Field(pattern=r"^https://gitlab\.com/", max_length=2_048)
    description: str | None = Field(default=None, max_length=2_000)
    archived: bool = False
    visibility: str = Field(default="public", max_length=30)
    topics: list[str] = Field(default_factory=list, max_length=100)
    created_at: datetime
    last_activity_at: datetime


class PyPiInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=300)
    version: str = Field(min_length=1, max_length=200)
    summary: str | None = Field(default=None, max_length=2_000)


class PyPiProjectRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    info: PyPiInfo


class NpmPackageRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2_000)
    dist_tags: dict[str, str] = Field(default_factory=dict, alias="dist-tags")
    modified: datetime | None = None

    @property
    def latest_version(self) -> str | None:
        return self.dist_tags.get("latest")


class MavenArtifactRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, max_length=1_000)
    g: str = Field(min_length=1, max_length=500)
    a: str = Field(min_length=1, max_length=500)
    latestVersion: str = Field(min_length=1, max_length=300)
    versionCount: int = Field(ge=0)
    timestamp: int = Field(ge=0)
    p: str | None = Field(default=None, max_length=100)


class MavenResponseBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    docs: list[MavenArtifactRecord] = Field(default_factory=list, max_length=10)


class MavenSearchResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    response: MavenResponseBody

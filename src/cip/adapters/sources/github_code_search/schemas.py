from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GitHubCodeRepository(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=300)
    full_name: str = Field(min_length=1, max_length=500)
    private: bool
    html_url: str = Field(min_length=1, max_length=2_000)


class GitHubCodeSearchItem(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=500)
    path: str = Field(min_length=1, max_length=2_000)
    sha: str = Field(min_length=7, max_length=100)
    url: str = Field(min_length=1, max_length=2_000)
    git_url: str = Field(min_length=1, max_length=2_000)
    html_url: str = Field(min_length=1, max_length=2_000)
    repository: GitHubCodeRepository


class GitHubCodeSearchResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_count: int = Field(ge=0)
    incomplete_results: bool
    items: tuple[GitHubCodeSearchItem, ...]

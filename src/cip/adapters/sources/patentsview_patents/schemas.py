from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PatentsViewAssignee(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    assignee_organization: str | None = Field(default=None, max_length=500)


class PatentsViewPatent(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    patent_id: str = Field(min_length=1, max_length=100)
    patent_title: str = Field(min_length=1, max_length=2_000)
    patent_date: str = Field(min_length=10, max_length=10)
    patent_type: str = Field(min_length=1, max_length=100)
    assignees: tuple[PatentsViewAssignee, ...] = Field(default_factory=tuple, max_length=50)


class PatentsViewPatentResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    error: bool
    count: int = Field(ge=0, le=20)
    total_hits: int = Field(ge=0)
    patents: tuple[PatentsViewPatent, ...] = Field(default_factory=tuple, max_length=20)

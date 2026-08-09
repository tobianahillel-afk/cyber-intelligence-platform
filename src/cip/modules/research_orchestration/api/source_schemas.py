from __future__ import annotations

from pydantic import BaseModel


class ResearchSourceOptionResponse(BaseModel):
    rank: int
    source_id: str
    tool_id: str
    mode: str
    authorized: bool
    executable: bool
    manual_link_allowed: bool
    freshness_score: float
    value_score: float
    estimated_cost: float
    quota_remaining: int | None
    risk_level: str


class ResearchSourceOptionsResponse(BaseModel):
    purpose: str
    data_category: str
    items: list[ResearchSourceOptionResponse]

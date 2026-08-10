from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PhishTankFeedRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    phish_id: int = Field(gt=0)
    phish_detail_url: str = Field(pattern=r"^https?://", max_length=2_048)
    url: str = Field(min_length=1, max_length=2_048)
    submission_time: datetime
    verified: Literal["yes"]
    verification_time: datetime
    online: Literal["yes"]
    target: str | None = Field(default=None, max_length=500)

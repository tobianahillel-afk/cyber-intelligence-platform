from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

_CRAWL_ID = re.compile(r"^CC-MAIN-(\d{4})-(\d{2})$")


class CommonCrawlCollection(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str
    name: str
    timegate: str
    cdx_api: str = Field(alias="cdx-api")
    from_at: datetime = Field(alias="from")
    to_at: datetime = Field(alias="to")

    @field_validator("id")
    @classmethod
    def _valid_crawl_id(cls, value: str) -> str:
        if _CRAWL_ID.fullmatch(value) is None:
            raise ValueError("Common Crawl collection id is invalid")
        return value


class CommonCrawlCapture(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    timestamp: str = Field(pattern=r"^\d{14}$")
    url: str
    mime: str
    status: str = Field(pattern=r"^\d{3}$")
    digest: str
    length: int = Field(ge=0, le=10_000_000)
    offset: int = Field(ge=0)
    filename: str

    @field_validator("url", "mime", "digest", "filename")
    @classmethod
    def _required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("Common Crawl capture field cannot be blank")
        return value


def crawl_sort_key(crawl_id: str) -> tuple[int, int]:
    match = _CRAWL_ID.fullmatch(crawl_id)
    if match is None:
        raise ValueError("Common Crawl collection id is invalid")
    return int(match.group(1)), int(match.group(2))

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class IanaRdapBootstrap(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: str = Field(min_length=1, max_length=20)
    publication: datetime
    services: list[tuple[list[str], list[str]]] = Field(max_length=20_000)

    @model_validator(mode="after")
    def validate_services(self) -> IanaRdapBootstrap:
        for keys, urls in self.services:
            if not keys or not urls:
                raise ValueError("IANA RDAP bootstrap service entries cannot be empty")
            if len(keys) > 20_000 or len(urls) > 20:
                raise ValueError("IANA RDAP bootstrap service entry exceeds bounds")
        return self


class RdapEvent(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    eventAction: str = Field(min_length=1, max_length=100)
    eventDate: datetime


class PublicRdapObject(BaseModel):
    """Strict minimal public subset; entity/vCard/contact data is never materialized."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    objectClassName: str = Field(min_length=1, max_length=100)
    handle: str | None = Field(default=None, max_length=500)
    ldhName: str | None = Field(default=None, max_length=253)
    name: str | None = Field(default=None, max_length=500)
    type: str | None = Field(default=None, max_length=100)
    startAddress: str | None = Field(default=None, max_length=64)
    endAddress: str | None = Field(default=None, max_length=64)
    ipVersion: str | None = Field(default=None, max_length=20)
    startAutnum: int | None = Field(default=None, ge=0, le=4_294_967_295)
    endAutnum: int | None = Field(default=None, ge=0, le=4_294_967_295)
    status: list[str] = Field(default_factory=list, max_length=100)
    events: list[RdapEvent] = Field(default_factory=list, max_length=200)

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class W3cLink(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    href: str = Field(min_length=1, max_length=2_000)


class W3cAffiliation(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    id: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=300)


class W3cParticipation(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    links: dict[str, W3cLink] = Field(alias="_links", default_factory=dict)


class W3cParticipationsEmbedded(BaseModel):
    model_config = ConfigDict(extra="ignore")

    participations: tuple[W3cParticipation, ...] = Field(default_factory=tuple, max_length=20)


class W3cParticipationsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    embedded: W3cParticipationsEmbedded = Field(alias="_embedded")


class W3cSpecification(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True, str_strip_whitespace=True)

    shortname: str = Field(min_length=1, max_length=300)
    title: str = Field(min_length=1, max_length=1_000)
    shortlink: str | None = Field(default=None, max_length=2_000)
    links: dict[str, W3cLink] = Field(alias="_links", default_factory=dict)


class W3cSpecificationsEmbedded(BaseModel):
    model_config = ConfigDict(extra="ignore")

    specifications: tuple[W3cSpecification, ...] = Field(default_factory=tuple, max_length=20)


class W3cSpecificationsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    embedded: W3cSpecificationsEmbedded = Field(alias="_embedded")

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class BodaccIdentityAnnouncement(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    dateparution: date
    typeavis: str | None = None
    typeavis_lib: str | None = None
    familleavis: str | None = None
    familleavis_lib: str | None = None
    commercant: str | None = None
    ville: str | None = None
    registre: str | list[str] | None = None
    cp: str | None = None
    modificationsgenerales: str | None = None
    radiationaurcs: str | None = None
    url_complete: str | None = None

    def registration_text(self) -> str:
        if isinstance(self.registre, str):
            return self.registre
        if isinstance(self.registre, list):
            return " ".join(self.registre)
        return ""

    def status_family(self) -> str:
        return (self.familleavis or self.familleavis_lib or "").strip().casefold()


class BodaccIdentityResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_count: int = Field(ge=0)
    results: list[BodaccIdentityAnnouncement]

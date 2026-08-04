from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BoampNotice(BaseModel):
    model_config = ConfigDict(extra="ignore")

    idweb: str = Field(min_length=1, max_length=100)
    objet: str = Field(min_length=1, max_length=4_000)
    dateparution: date | datetime | str | None = None
    datelimitereponse: date | datetime | str | None = None
    nomacheteur: str = Field(min_length=1, max_length=500)
    etat: str | None = Field(default=None, max_length=100)
    nature_libelle: str | None = Field(default=None, max_length=500)
    type_avis: object | None = None
    descripteur_libelle: object | None = None
    type_marche: object | None = None
    titulaire: object | None = None
    url_avis: str | None = Field(default=None, max_length=2_000)

    @field_validator("idweb", "objet", "nomacheteur")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("required BOAMP text cannot be empty")
        return normalized

    def publication_timestamp(self) -> datetime | None:
        return _parse_datetime(self.dateparution)

    def deadline_timestamp(self) -> datetime | None:
        return _parse_datetime(self.datelimitereponse)

    def searchable_text(self) -> str:
        values = [
            self.objet,
            *_flatten_text(self.descripteur_libelle),
            *_flatten_text(self.type_marche),
            *_flatten_text(self.type_avis),
        ]
        return " ".join(values)

    def notice_url(self) -> str:
        if self.url_avis and self.url_avis.strip():
            return self.url_avis.strip()
        return f"https://www.boamp.fr/pages/avis/?q=idweb:{self.idweb}"


class BoampResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_count: int = Field(default=0, ge=0)
    results: list[BoampNotice] = Field(default_factory=list)


def _flatten_text(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        normalized = value.strip()
        return [normalized] if normalized else []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_flatten_text(item))
        return result
    if isinstance(value, dict):
        result = []
        for item in value.values():
            result.extend(_flatten_text(item))
        return result
    return []


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if not isinstance(value, str):
        return None
    normalized = value.strip().replace("Z", "+00:00")
    if not normalized:
        return None
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        for pattern in ("%Y%m%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(normalized, pattern)
            except ValueError:
                continue
    return None

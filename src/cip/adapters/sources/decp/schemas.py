from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DecpContract(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, max_length=300)
    nature: str | None = Field(default=None, max_length=200)
    objet: str = Field(min_length=1, max_length=4_000)
    codecpv: str | None = Field(default=None, max_length=100)
    procedure: str | None = Field(default=None, max_length=500)
    acheteur_id: str = Field(min_length=1, max_length=100)
    acheteur_nom: str = Field(min_length=1, max_length=500)
    dureemois: int | str | None = None
    datenotification: date | datetime | str | None = None
    datepublicationdonnees: date | datetime | str | None = None
    montant: Decimal | int | float | str | None = None
    titulaire_denominationsociale_1: str | None = Field(default=None, max_length=500)
    titulaire_id_1: str | None = Field(default=None, max_length=200)
    titulaire_typeidentifiant_1: str | None = Field(default=None, max_length=100)
    titulaire_denominationsociale_2: str | None = Field(default=None, max_length=500)
    titulaire_id_2: str | None = Field(default=None, max_length=200)
    titulaire_typeidentifiant_2: str | None = Field(default=None, max_length=100)
    titulaire_denominationsociale_3: str | None = Field(default=None, max_length=500)
    titulaire_id_3: str | None = Field(default=None, max_length=200)
    titulaire_typeidentifiant_3: str | None = Field(default=None, max_length=100)
    booleanmodification: bool | str | int | None = None
    idmodification: str | None = Field(default=None, max_length=300)
    objetmodification: str | None = Field(default=None, max_length=4_000)
    datenotificationmodification: date | datetime | str | None = None
    dureemoismodification: int | str | None = None
    datepublicationdonneesmodification: date | datetime | str | None = None
    montantmodification: Decimal | int | float | str | None = None
    titulairesmodification: object | None = None
    source: str | None = Field(default=None, max_length=500)
    updated_at: date | datetime | str | None = None

    @field_validator("id", "objet", "acheteur_id", "acheteur_nom")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("required DECP text cannot be empty")
        return normalized

    def is_modification(self) -> bool:
        value = self.booleanmodification
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, str):
            return value.strip().casefold() in {"1", "true", "vrai", "yes", "oui"}
        return bool(
            self.idmodification
            or self.objetmodification
            or self.datepublicationdonneesmodification
            or self.montantmodification is not None
        )

    def effective_title(self) -> str:
        if self.is_modification() and self.objetmodification:
            normalized = self.objetmodification.strip()
            if normalized:
                return normalized
        return self.objet

    def notification_timestamp(self) -> datetime | None:
        if self.is_modification():
            modified = _parse_datetime(self.datenotificationmodification)
            if modified is not None:
                return modified
        return _parse_datetime(self.datenotification)

    def publication_timestamp(self) -> datetime | None:
        if self.is_modification():
            modified = _parse_datetime(self.datepublicationdonneesmodification)
            if modified is not None:
                return modified
        return _parse_datetime(self.datepublicationdonnees) or _parse_datetime(self.updated_at)

    def duration_months(self) -> int | None:
        value = self.dureemoismodification if self.is_modification() else self.dureemois
        if value is None:
            return None
        try:
            duration = int(str(value).strip())
        except ValueError:
            return None
        return duration if 0 < duration <= 1_200 else None

    def amount_value(self) -> Decimal | None:
        value = self.montantmodification if self.is_modification() else self.montant
        if value is None:
            return None
        normalized = str(value).strip().replace(" ", "").replace(",", ".")
        try:
            amount = Decimal(normalized)
        except InvalidOperation:
            return None
        return amount if amount >= 0 else None

    def buyer_identifier(self) -> str:
        return self.acheteur_id.strip()

    def titulars(self) -> tuple[tuple[str, str | None, str | None], ...]:
        base = [
            (
                self.titulaire_denominationsociale_1,
                self.titulaire_id_1,
                self.titulaire_typeidentifiant_1,
            ),
            (
                self.titulaire_denominationsociale_2,
                self.titulaire_id_2,
                self.titulaire_typeidentifiant_2,
            ),
            (
                self.titulaire_denominationsociale_3,
                self.titulaire_id_3,
                self.titulaire_typeidentifiant_3,
            ),
        ]
        values = _extract_modified_titulars(self.titulairesmodification)
        if self.is_modification() and values:
            return values
        result: list[tuple[str, str | None, str | None]] = []
        for name, identifier, identifier_type in base:
            normalized_name = _optional_text(name)
            if normalized_name is None:
                continue
            result.append(
                (
                    normalized_name,
                    _optional_text(identifier),
                    _optional_text(identifier_type),
                )
            )
        return tuple(result)

    def searchable_text(self) -> str:
        return " ".join(
            value
            for value in (
                self.objet,
                self.objetmodification or "",
                self.codecpv or "",
                self.procedure or "",
                self.nature or "",
            )
            if value
        )


class DecpResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_count: int = Field(default=0, ge=0)
    results: list[DecpContract] = Field(default_factory=list)


def _extract_modified_titulars(
    value: object,
) -> tuple[tuple[str, str | None, str | None], ...]:
    if not isinstance(value, list):
        return ()
    result: list[tuple[str, str | None, str | None]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _first_mapping_text(
            item,
            ("denominationSociale", "denominationsociale", "nom", "name"),
        )
        if name is None:
            continue
        identifier = _first_mapping_text(item, ("id", "identifiant", "siret", "siren"))
        identifier_type = _first_mapping_text(
            item,
            ("typeIdentifiant", "typeidentifiant", "type"),
        )
        result.append((name, identifier, identifier_type))
    return tuple(result)


def _first_mapping_text(payload: dict[object, object], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if key not in payload:
            continue
        value = payload[key]
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


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
        for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"):
            try:
                return datetime.strptime(normalized, pattern)
            except ValueError:
                continue
    return None

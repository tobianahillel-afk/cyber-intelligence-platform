from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlaceGeoPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)


class PlaceAward(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    annee_de_notification: int | None = None
    entite_publique: str
    entite_d_achat: str | None = None
    code_postal_entite_d_achat: str | None = None
    nom_attributaire: str | None = None
    siret_attributaire: str | None = None
    date_de_notification: date
    code_postal_attributaire: str | None = None
    ville: str | None = None
    nature_du_marche: str | None = None
    objet_du_marche: str
    tranche_budgetaire: str | None = None
    montant: Decimal | None = None
    attributaire_est_une_pme: str | None = None
    geocode_att: PlaceGeoPoint | None = None

    @field_validator("entite_publique", "objet_du_marche")
    @classmethod
    def _required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("required PLACE text field cannot be blank")
        return value

    @field_validator("nom_attributaire")
    @classmethod
    def _optional_awardee(cls, value: str | None) -> str | None:
        return value or None

    @field_validator("annee_de_notification")
    @classmethod
    def _valid_notification_year(cls, value: int | None) -> int | None:
        if value is not None and not 1900 <= value <= 2100:
            raise ValueError("PLACE notification year is outside supported bounds")
        return value

    @field_validator("montant")
    @classmethod
    def _non_negative_amount(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value < 0:
            raise ValueError("PLACE amount cannot be negative")
        return value

    def buyer_name(self) -> str:
        return self.entite_d_achat or self.entite_publique

    def searchable_text(self) -> str:
        return " ".join(
            value
            for value in (
                self.entite_publique,
                self.entite_d_achat,
                self.nature_du_marche,
                self.objet_du_marche,
                self.nom_attributaire,
            )
            if value
        )


class PlaceAwardsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_count: int
    results: tuple[PlaceAward, ...]

    @field_validator("total_count")
    @classmethod
    def _non_negative_total(cls, value: int) -> int:
        if value < 0:
            raise ValueError("PLACE total_count cannot be negative")
        return value

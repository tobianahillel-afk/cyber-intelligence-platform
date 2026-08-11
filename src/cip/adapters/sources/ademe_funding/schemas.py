from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AdemeFundingLine(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(alias="_id")
    nom: str = Field(alias="nomBeneficiaire")
    objet: str
    nature: str
    date: str = Field(alias="dateConvention")
    montant: Decimal

    @field_validator("id", "nom", "objet", "nature", "date")
    @classmethod
    def _required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("required ADEME funding field cannot be blank")
        return value

    @field_validator("montant")
    @classmethod
    def _non_negative_amount(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("ADEME funding amount cannot be negative")
        return value


class AdemeFundingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int
    results: tuple[AdemeFundingLine, ...]
    next: str | None = None

    @field_validator("total")
    @classmethod
    def _non_negative_total(cls, value: int) -> int:
        if value < 0:
            raise ValueError("ADEME total cannot be negative")
        return value

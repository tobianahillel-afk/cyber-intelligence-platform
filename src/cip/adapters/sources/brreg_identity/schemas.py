from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BrregLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    href: str


class BrregOrganizationForm(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    kode: str
    beskrivelse: str | None = None
    utgaatt: date | None = None
    links: dict[str, BrregLink] | None = Field(default=None, alias="_links")


class BrregIndustryCode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kode: str
    beskrivelse: str | None = None


class BrregAddress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kommune: str | None = None
    landkode: str | None = None
    postnummer: str | None = None
    adresse: tuple[str, ...] = ()
    land: str | None = None
    kommunenummer: str | None = None
    poststed: str | None = None

    def single_line(self) -> str | None:
        parts = [*self.adresse]
        locality = " ".join(
            value for value in (self.postnummer, self.poststed) if value
        ).strip()
        if locality:
            parts.append(locality)
        normalized = ", ".join(value.strip() for value in parts if value.strip())
        return normalized or None


class BrregHistoricalName(BaseModel):
    model_config = ConfigDict(extra="forbid")

    navn: str
    fraDato: str | None = None
    tilDato: str | None = None


class BrregEntity(BaseModel):
    model_config = ConfigDict(extra="allow", str_strip_whitespace=True, populate_by_name=True)

    respons_klasse: str | None = None
    organisasjonsnummer: str
    navn: str
    organisasjonsform: BrregOrganizationForm
    historiskeNavn: tuple[BrregHistoricalName, ...] = ()
    postadresse: BrregAddress | None = None
    forretningsadresse: BrregAddress | None = None
    registreringsdatoEnhetsregisteret: date | None = None
    stiftelsesdato: date | None = None
    slettedato: date | None = None
    registrertIForetaksregisteret: bool | None = None
    konkurs: bool | None = None
    underAvvikling: bool | None = None
    underTvangsavviklingEllerTvangsopplosning: bool | None = None
    naeringskode1: BrregIndustryCode | None = None
    naeringskode2: BrregIndustryCode | None = None
    naeringskode3: BrregIndustryCode | None = None
    antallAnsatte: int | None = None
    overordnetEnhet: str | None = None
    hjemmeside: str | None = None
    links: dict[str, BrregLink] | None = Field(default=None, alias="_links")

    @field_validator("organisasjonsnummer")
    @classmethod
    def _valid_org_number(cls, value: str) -> str:
        normalized = "".join(character for character in value if character.isdigit())
        if len(normalized) != 9:
            raise ValueError("BRREG organisation number must contain 9 digits")
        return normalized

    @field_validator("navn")
    @classmethod
    def _required_name(cls, value: str) -> str:
        if not value:
            raise ValueError("BRREG entity name cannot be blank")
        return value

    @field_validator("antallAnsatte")
    @classmethod
    def _non_negative_employees(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("BRREG employee count cannot be negative")
        return value

    def aliases(self) -> tuple[str, ...]:
        values = [item.navn for item in self.historiskeNavn if item.navn != self.navn]
        return tuple(dict.fromkeys(values))

    def business_address(self) -> BrregAddress | None:
        return self.forretningsadresse or self.postadresse

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class RechercheEtablissement(BaseModel):
    model_config = ConfigDict(extra="ignore")

    siret: str
    etat_administratif: str | None = None
    statut_diffusion_etablissement: str | None = None
    est_siege: bool = False
    adresse: str | None = None
    code_postal: str | None = None
    libelle_commune: str | None = None
    activite_principale: str | None = None
    date_creation: date | None = None
    date_fermeture: date | None = None
    date_mise_a_jour: datetime | None = None
    nom_commercial: str | None = None
    liste_enseignes: list[str] = Field(default_factory=list)


class RechercheEntrepriseResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    siren: str
    nom_complet: str
    nom_raison_sociale: str | None = None
    sigle: str | None = None
    etat_administratif: str | None = None
    nature_juridique: str | None = None
    activite_principale: str | None = None
    date_creation: date | None = None
    date_fermeture: date | None = None
    date_mise_a_jour: datetime | None = None
    statut_diffusion: str | None = None
    siege: RechercheEtablissement | None = None
    matching_etablissements: list[RechercheEtablissement] = Field(default_factory=list)

    def official_name(self) -> str:
        return (self.nom_raison_sociale or self.nom_complet).strip()

    def public_aliases(self) -> tuple[str, ...]:
        values = (self.nom_complet, self.sigle)
        return tuple(value.strip() for value in values if value and value.strip())


class RechercheEntreprisesResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    results: list[RechercheEntrepriseResult]
    total_results: int = Field(default=0, ge=0)
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=10, ge=1, le=25)
    total_pages: int = Field(default=1, ge=0)

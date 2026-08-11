from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from cip.adapters.sources.place_awards.mapper import map_place_award
from cip.adapters.sources.place_awards.schemas import PlaceAward

NOW = datetime(2026, 8, 11, 8, 30, tzinfo=UTC)


def test_missing_live_awardee_keeps_contract_without_invented_party() -> None:
    award = PlaceAward.model_validate(
        {
            "annee_de_notification": "2017",
            "entite_publique": "Ministère exemple",
            "entite_d_achat": "Service des achats",
            "code_postal_entite_d_achat": "75001",
            "nom_attributaire": None,
            "siret_attributaire": None,
            "date_de_notification": "2017-04-03",
            "code_postal_attributaire": None,
            "ville": None,
            "nature_du_marche": "Services",
            "objet_du_marche": "Prestations de maintenance",
            "tranche_budgetaire": None,
            "montant": 25000,
            "attributaire_est_une_pme": None,
            "geocode_att": {"lon": 2.35, "lat": 48.85},
        }
    )
    mapped = map_place_award(
        award,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=3650),
    )

    assert mapped.observation.source_record_type == "procurement_award"
    assert mapped.procurement.contract is not None
    assert mapped.procurement.contract.parties == ()

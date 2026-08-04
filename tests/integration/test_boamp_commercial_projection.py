from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cip.adapters.sources.boamp.mapper import map_boamp_notice
from cip.adapters.sources.boamp.schemas import BoampNotice
from cip.modules.evidence.infrastructure.models import EvidenceRecord
from cip.modules.opportunities.infrastructure.models import (
    CommercialSignalRecord,
    OpportunityRecord,
)
from cip.modules.opportunities.infrastructure.projections import (
    persist_commercial_projections,
)
from cip.modules.opportunities.infrastructure.queries import get_opportunity_detail
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 4, 10, 0, tzinfo=UTC)


def test_boamp_projection_is_idempotent_and_visible_in_inbox() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)
    mapped = map_boamp_notice(
        BoampNotice.model_validate(_notice()),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=730),
    )
    assert mapped is not None and mapped.projection is not None

    with factory() as session:
        first_ids = persist_commercial_projections(
            session,
            (mapped.projection,),
            now=NOW,
        )
        second_ids = persist_commercial_projections(
            session,
            (mapped.projection,),
            now=NOW,
        )
        session.commit()
        _assert_counts(session)
        assert first_ids == second_ids
        assert len(first_ids) == 1
        detail = get_opportunity_detail(session, first_ids[0])
        assert detail.opportunity.organization == "Métropole Exemple"
        assert detail.opportunity.country == "FR"
        assert detail.opportunity.evidence_count == 1
        assert detail.opportunity.trigger.startswith("1 public tender")
        assert detail.evidence[0].source_id == "boamp"
        assert detail.evidence[0].source_url.endswith("26-654321")


def _assert_counts(session: Session) -> None:
    assert session.scalar(select(func.count()).select_from(OrganizationRecord)) == 1
    assert session.scalar(select(func.count()).select_from(EvidenceRecord)) == 1
    assert session.scalar(select(func.count()).select_from(CommercialSignalRecord)) == 1
    assert session.scalar(select(func.count()).select_from(OpportunityRecord)) == 1


def _notice() -> dict[str, object]:
    return {
        "idweb": "26-654321",
        "objet": "Acquisition d'une plateforme SIEM et service SOC managé",
        "dateparution": "2026-08-04",
        "datelimitereponse": "2026-09-10T12:00:00Z",
        "nomacheteur": "Métropole Exemple",
        "etat": "initial",
        "nature_libelle": "Avis de marché",
        "type_avis": ["Avis de marché"],
        "descripteur_libelle": ["Cybersécurité"],
        "type_marche": ["Services"],
        "url_avis": "https://www.boamp.fr/avis/26-654321",
    }

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from cip.adapters.sources.boamp.mapper import map_boamp_notice
from cip.adapters.sources.boamp.schemas import BoampNotice
from cip.modules.opportunities.domain.entities import SignalType

NOW = datetime(2026, 8, 4, 10, 0, tzinfo=UTC)


def test_mapper_creates_deterministic_actionable_projection() -> None:
    notice = BoampNotice.model_validate(_notice())
    retention = NOW + timedelta(days=730)

    first = map_boamp_notice(
        notice,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=retention,
    )
    second = map_boamp_notice(
        notice,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=retention,
    )

    assert first is not None and second is not None
    assert first.projection is not None and second.projection is not None
    assert first.observation.source_record_type == "procurement_notice"
    assert first.observation.source_url == "https://www.boamp.fr/avis/26-123456"
    assert first.observation.payload_hash_sha256 == first.projection.evidence.content_hash_sha256
    assert first.projection.organization.id == second.projection.organization.id
    assert first.projection.evidence.id == second.projection.evidence.id
    assert first.projection.signal.id == second.projection.signal.id
    assert first.projection.organization.country_code == "FR"
    assert first.projection.signal.signal_type is SignalType.PUBLIC_TENDER
    assert first.projection.signal.matched_terms[:2] == ("siem", "soc")
    assert first.projection.signal.expires_at == datetime(2026, 8, 30, 12, tzinfo=UTC)


def test_mapper_keeps_cancellation_result_and_expired_notice_without_opportunity() -> None:
    cases = (
        (
            _notice(idweb="26-cancel", etat="ANNULATION"),
            "procurement_cancellation",
        ),
        (
            _notice(idweb="26-result", type_avis=["Avis de résultat d'attribution"]),
            "procurement_result",
        ),
        (
            _notice(
                idweb="26-expired",
                datelimitereponse="2026-08-01T12:00:00Z",
            ),
            "procurement_notice",
        ),
    )

    for payload, expected_type in cases:
        mapped = map_boamp_notice(
            BoampNotice.model_validate(payload),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=730),
        )
        assert mapped is not None
        assert mapped.observation.source_record_type == expected_type
        assert mapped.projection is None


def test_mapper_keeps_actionable_rectification() -> None:
    mapped = map_boamp_notice(
        BoampNotice.model_validate(_notice(idweb="26-rect", etat="rectificatif")),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=730),
    )

    assert mapped is not None
    assert mapped.observation.source_record_type == "procurement_rectification"
    assert mapped.projection is not None


def test_mapper_drops_non_cyber_notice() -> None:
    mapped = map_boamp_notice(
        BoampNotice.model_validate(
            _notice(
                objet="Fourniture de mobilier de bureau",
                descripteur_libelle=["Mobilier"],
                type_marche=["Fournitures"],
                type_avis=["Avis de marché"],
            )
        ),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=730),
    )

    assert mapped is None


def _notice(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "idweb": "26-123456",
        "objet": "Service SIEM et centre opérationnel SOC",
        "dateparution": "2026-08-04",
        "datelimitereponse": "2026-08-30T12:00:00Z",
        "nomacheteur": "Ville Exemple",
        "etat": "initial",
        "nature_libelle": "Avis de marché",
        "type_avis": ["Avis de marché"],
        "descripteur_libelle": ["Cybersécurité"],
        "type_marche": ["Services"],
        "titulaire": None,
        "url_avis": "https://www.boamp.fr/avis/26-123456",
    }
    payload.update(changes)
    return payload

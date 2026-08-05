from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from cip.adapters.sources.boamp.mapper import map_boamp_notice
from cip.adapters.sources.boamp.schemas import BoampNotice
from cip.modules.opportunities.domain.entities import SignalType
from cip.modules.procurement_history.domain.models import (
    PartyResolutionStatus,
    ProcurementPublicationKind,
)
from cip.modules.service_taxonomy.domain.models import CyberServiceFamily

NOW = datetime(2026, 8, 4, 10, 0, tzinfo=UTC)


def test_mapper_creates_deterministic_actionable_projection_and_history() -> None:
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
    assert first.procurement.publication.kind is ProcurementPublicationKind.NOTICE
    assert first.procurement.contract is None
    assert first.procurement.publication.buyer_organization_id == first.buyer.id


def test_mapper_keeps_cancellation_result_and_expired_notice_without_opportunity() -> None:
    cases = (
        (
            _notice(idweb="26-cancel", etat="ANNULATION"),
            "procurement_cancellation",
            ProcurementPublicationKind.CANCELLATION,
        ),
        (
            _notice(idweb="26-result", type_avis=["Avis de résultat d'attribution"]),
            "procurement_result",
            ProcurementPublicationKind.RESULT,
        ),
        (
            _notice(
                idweb="26-expired",
                datelimitereponse="2026-08-01T12:00:00Z",
            ),
            "procurement_notice",
            ProcurementPublicationKind.NOTICE,
        ),
    )

    for payload, expected_type, expected_kind in cases:
        mapped = map_boamp_notice(
            BoampNotice.model_validate(payload),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=730),
        )
        assert mapped is not None
        assert mapped.observation.source_record_type == expected_type
        assert mapped.projection is None
        assert mapped.procurement.publication.kind is expected_kind
        assert mapped.procurement.contract is None


def test_mapper_creates_unresolved_provider_contract_from_published_award() -> None:
    mapped = map_boamp_notice(
        BoampNotice.model_validate(
            _notice(
                idweb="26-award",
                objet="Attribution d'un accord-cadre audit ISO 27001 et PAM",
                type_avis=["Avis de résultat d'attribution"],
                titulaire=[
                    {"denomination": "Provider One SAS", "siret": "11111111111111"},
                    {"raisonSociale": "Provider Two SA", "siret": "22222222222222"},
                ],
            )
        ),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=730),
    )

    assert mapped is not None
    assert mapped.projection is None
    assert mapped.procurement.publication.kind is ProcurementPublicationKind.AWARD
    contract = mapped.procurement.contract
    assert contract is not None
    assert tuple(party.published_name for party in contract.parties) == (
        "Provider One SAS",
        "Provider Two SA",
    )
    assert all(
        party.resolution_status is PartyResolutionStatus.UNRESOLVED
        for party in contract.parties
    )
    assert {match.family for match in contract.service_families} == {
        CyberServiceFamily.AUDIT_RISK_ASSESSMENT,
        CyberServiceFamily.GRC_COMPLIANCE,
        CyberServiceFamily.IAM_IGA_PAM_ZERO_TRUST,
    }


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
    assert mapped.procurement.publication.kind is ProcurementPublicationKind.RECTIFICATION


def test_mapper_accepts_non_siem_cyber_service_and_drops_unrelated_notice() -> None:
    pentest = map_boamp_notice(
        BoampNotice.model_validate(
            _notice(
                idweb="26-pentest",
                objet="Prestations de tests d'intrusion et red team",
                descripteur_libelle=["Sécurité applicative"],
            )
        ),
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=730),
    )
    unrelated = map_boamp_notice(
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

    assert pentest is not None
    assert pentest.projection is not None
    assert "tests d'intrusion" in pentest.projection.signal.matched_terms
    assert unrelated is None


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

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.ted_search.client import (
    TedSearchClient,
    TedSourceResponseError,
)
from cip.adapters.sources.ted_search.mapper import map_ted_notice
from cip.adapters.sources.ted_search.schemas import TedNotice, TedSearchResponse
from cip.modules.opportunities.domain.entities import SignalType
from cip.modules.procurement_history.domain.models import (
    DateBasis,
    PartyResolutionStatus,
    ProcurementPublicationKind,
)
from cip.modules.service_taxonomy.domain.models import CyberServiceFamily

NOW = datetime(2026, 8, 4, 10, 0, tzinfo=UTC)


def test_client_posts_bounded_selected_field_search() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["body"] = request.read().decode()
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"notices": []},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        result = TedSearchClient(
            http_client,
            search_url="https://api.ted.europa.eu/v3/notices/search",
        ).fetch()

    body = str(captured["body"])
    assert captured["method"] == "POST"
    assert '"scope":"ALL"' in body
    assert '"limit":100' in body
    assert '"procedure-identifier"' in body
    assert '"winner-name"' in body
    assert '"contract-conclusion-date"' in body
    assert TedSearchResponse.model_validate_json(result.body).notices == []


def test_client_rejects_non_json_and_oversized_responses() -> None:
    def wrong_type(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, text="no")

    with (
        httpx.Client(transport=httpx.MockTransport(wrong_type)) as http_client,
        pytest.raises(TedSourceResponseError, match="content type"),
    ):
        TedSearchClient(http_client, search_url="https://example.test/search").fetch()

    def oversized(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "content-type": "application/json",
                "content-length": str(TedSearchClient.MAX_RESPONSE_BYTES + 1),
            },
            content=b"{}",
        )

    with (
        httpx.Client(transport=httpx.MockTransport(oversized)) as http_client,
        pytest.raises(TedSourceResponseError, match="size limit"),
    ):
        TedSearchClient(http_client, search_url="https://example.test/search").fetch()


def test_schema_normalizes_localized_fields_dates_and_contract_values() -> None:
    notice = TedNotice.model_validate(
        _notice_payload(
            **{
                "notice-title": {"fra": "Supervision SIEM"},
                "buyer-name": {"eng": ["Public Buyer"]},
                "publication-date": "20260804",
                "deadline-receipt-tender-date-lot": ["2026-08-20T12:00:00Z"],
                "procedure-identifier": ["7e9a7792-e8fd-4f3d-bdad-111111111111"],
                "winner-name": {"eng": ["Provider One"]},
                "tender-value": ["250000.00"],
                "tender-value-cur": ["eur"],
                "contract-conclusion-date": ["2026-08-10"],
            }
        )
    )

    assert notice.title() == "Supervision SIEM"
    assert notice.buyer() == "Public Buyer"
    assert notice.country() == "FRA"
    assert notice.procedure_id() == "7e9a7792-e8fd-4f3d-bdad-111111111111"
    assert notice.winner_names() == ("Provider One",)
    assert notice.tender_values() == ("250000.00",)
    assert notice.tender_currencies() == ("EUR",)
    assert notice.publication_timestamp() == datetime(2026, 8, 4)
    assert notice.deadline_timestamp() == datetime(2026, 8, 20, 12, tzinfo=UTC)
    assert notice.conclusion_timestamp() == datetime(2026, 8, 10)


def test_mapper_creates_deterministic_active_notice_and_history() -> None:
    notice = TedNotice.model_validate(_notice_payload())
    retention = NOW + timedelta(days=730)

    first = map_ted_notice(
        notice,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=retention,
    )
    second = map_ted_notice(
        notice,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=retention,
    )

    assert first is not None and second is not None
    assert first.projection is not None and second.projection is not None
    assert first.projection.organization.id == second.projection.organization.id
    assert first.projection.evidence.id == second.projection.evidence.id
    assert first.projection.signal.id == second.projection.signal.id
    assert first.buyer.country_code == "FR"
    assert first.projection.signal.signal_type is SignalType.PUBLIC_TENDER
    assert first.projection.signal.matched_terms == ("siem", "soc")
    assert first.projection.signal.evidence_id == first.projection.evidence.id
    assert first.observation.source_url.endswith("123456-2026/html")
    assert first.observation.payload_hash_sha256 == first.projection.evidence.content_hash_sha256
    assert first.procurement.publication.kind is ProcurementPublicationKind.NOTICE
    assert first.procurement.contract is None


def test_mapper_creates_award_contract_without_current_signal() -> None:
    notice = TedNotice.model_validate(
        _notice_payload(
            **{
                "publication-number": "654321-2026",
                "notice-title": {"eng": "Award of ISO 27001 audit and PAM services"},
                "deadline-receipt-tender-date-lot": None,
                "notice-type": ["can-standard"],
                "procedure-identifier": ["7e9a7792-e8fd-4f3d-bdad-222222222222"],
                "contract-identifier": ["CON-0001"],
                "contract-title": {"eng": "Audit and PAM framework contract"},
                "winner-name": {"eng": ["Provider One SAS"]},
                "winner-identifier": ["FR-123456789"],
                "winner-decision-date": ["2026-08-08"],
                "contract-conclusion-date": ["2026-08-10"],
                "tender-value": ["250000.00"],
                "tender-value-cur": ["EUR"],
            }
        )
    )

    mapped = map_ted_notice(
        notice,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=730),
    )

    assert mapped is not None
    assert mapped.projection is None
    assert mapped.procurement.publication.kind is ProcurementPublicationKind.AWARD
    contract = mapped.procurement.contract
    assert contract is not None
    assert contract.contract_key.endswith("CON-0001")
    assert contract.title == "Audit and PAM framework contract"
    assert contract.award_date == date(2026, 8, 8)
    assert contract.conclusion_date == date(2026, 8, 10)
    assert contract.conclusion_date_basis is DateBasis.PUBLISHED
    assert contract.amount is not None
    assert contract.amount.value == Decimal("250000.00")
    assert contract.amount.currency == "EUR"
    assert contract.parties[0].published_name == "Provider One SAS"
    assert contract.parties[0].official_identifier == "FR-123456789"
    assert (
        contract.parties[0].resolution_status
        is PartyResolutionStatus.UNRESOLVED
    )
    assert {match.family for match in contract.service_families} == {
        CyberServiceFamily.AUDIT_RISK_ASSESSMENT,
        CyberServiceFamily.GRC_COMPLIANCE,
        CyberServiceFamily.IAM_IGA_PAM_ZERO_TRUST,
    }


def test_mapper_accepts_non_siem_cyber_service_and_drops_false_positive() -> None:
    pentest = TedNotice.model_validate(
        _notice_payload(
            **{
                "publication-number": "123457-2026",
                "notice-title": {"eng": "Penetration testing and red team services"},
            }
        )
    )
    unrelated = TedNotice.model_validate(
        _notice_payload(**{"notice-title": {"eng": "Office furniture supply"}})
    )

    mapped = map_ted_notice(
        pentest,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=NOW + timedelta(days=30),
    )

    assert mapped is not None
    assert mapped.projection is not None
    assert "penetration test" in mapped.projection.signal.matched_terms
    assert (
        map_ted_notice(
            unrelated,
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=NOW + timedelta(days=30),
        )
        is None
    )


def _notice_payload(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "publication-number": "123456-2026",
        "notice-title": {"eng": "SIEM and SOC managed security service"},
        "buyer-name": {"eng": ["Ville Exemple"]},
        "buyer-country": ["FRA"],
        "publication-date": "2026-08-04",
        "deadline-receipt-tender-date-lot": ["2026-08-20T12:00:00Z"],
        "classification-cpv": ["72000000"],
        "notice-type": ["cn-standard"],
        "procedure-identifier": ["7e9a7792-e8fd-4f3d-bdad-000000000001"],
        "contract-identifier": None,
        "contract-conclusion-date": None,
        "winner-decision-date": None,
        "winner-name": None,
        "winner-identifier": None,
        "contract-title": None,
        "tender-value": None,
        "tender-value-cur": None,
    }
    payload.update(changes)
    return payload

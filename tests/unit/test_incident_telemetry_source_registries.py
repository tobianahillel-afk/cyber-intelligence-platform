from __future__ import annotations

from pathlib import Path

from cip.modules.collection_orchestration.infrastructure.schedule_loader import (
    load_collection_schedules,
)
from cip.modules.source_governance.domain.models import AuthorizationStatus, SourceStatus
from cip.modules.source_governance.infrastructure.registry import load_source_registry
from cip.modules.source_portfolio.domain.models import CatalogStatus
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio

INCIDENT_SOURCE_PATH = Path("policies/sources.incidents.yml")
TELEMETRY_SOURCE_PATH = Path("policies/sources.threat_telemetry.yml")
INCIDENT_PORTFOLIO_PATH = Path("policies/source_portfolio.incidents.yml")
TELEMETRY_PORTFOLIO_PATH = Path("policies/source_portfolio.threat_telemetry.yml")
INCIDENT_SCHEDULE_PATH = Path("policies/collection_schedules.incidents.yml")
TELEMETRY_SCHEDULE_PATH = Path("policies/collection_schedules.threat_telemetry.yml")


def test_sec_source_is_enabled_with_exact_metadata_only_authorization() -> None:
    entry = _source(INCIDENT_SOURCE_PATH, "sec-cyber-disclosures")

    assert entry.policy.status is SourceStatus.ENABLED
    assert entry.authorization.status is AuthorizationStatus.APPROVED
    assert entry.authorization.approved_hosts == {"data.sec.gov"}
    assert entry.authorization.approved_path_prefixes == ("/submissions/",)
    assert entry.authorization.approved_purposes == {"incident-intelligence"}
    assert entry.authorization.automated_collection_allowed is True
    assert entry.policy.raw_content_storage is False
    assert entry.authorization.raw_storage_allowed is False


def test_phishtank_source_is_enabled_with_exact_metadata_only_authorization() -> None:
    entry = _source(TELEMETRY_SOURCE_PATH, "phishtank-verified-online")

    assert entry.policy.status is SourceStatus.ENABLED
    assert entry.authorization.status is AuthorizationStatus.APPROVED
    assert entry.authorization.approved_hosts == {"data.phishtank.com"}
    assert entry.authorization.approved_path_prefixes == ("/data/",)
    assert entry.authorization.approved_purposes == {"threat-telemetry"}
    assert entry.authorization.automated_collection_allowed is True
    assert entry.policy.raw_content_storage is False
    assert entry.authorization.raw_storage_allowed is False


def test_sa04_portfolios_are_executable_without_compromise_or_opportunity_authority() -> None:
    sec = _portfolio(INCIDENT_PORTFOLIO_PATH, "sec-cyber-disclosures")
    phishtank = _portfolio(TELEMETRY_PORTFOLIO_PATH, "phishtank-verified-online")

    assert sec.status is CatalogStatus.EXECUTABLE
    assert sec.executable is True
    assert sec.metadata["filing_narrative_collection"] == "forbidden"
    assert sec.metadata["global_issuer_enumeration"] == "forbidden"
    assert sec.metadata["automatic_opportunity"] == "forbidden"
    assert sec.metadata["autonomous_outreach"] == "forbidden"

    assert phishtank.status is CatalogStatus.EXECUTABLE
    assert phishtank.executable is True
    assert phishtank.metadata["phishing_url_visit"] == "forbidden"
    assert phishtank.metadata["direct_indicator_connection"] == "forbidden"
    assert phishtank.metadata["target_brand_as_compromise"] == "forbidden"
    assert phishtank.metadata["organization_compromise_inference"] == "forbidden"
    assert phishtank.metadata["automatic_opportunity"] == "forbidden"


def test_sa04_schedules_are_present_but_disabled_by_default() -> None:
    schedules = (
        *load_collection_schedules(INCIDENT_SCHEDULE_PATH),
        *load_collection_schedules(TELEMETRY_SCHEDULE_PATH),
    )

    assert {(item.source_id, item.adapter_id) for item in schedules} == {
        ("sec-cyber-disclosures", "sec-submissions-item-1-05"),
        ("phishtank-verified-online", "phishtank-online-valid-json"),
    }
    assert all(schedule.enabled is False for schedule in schedules)


def _source(path: Path, source_id: str):
    return {entry.policy.id: entry for entry in load_source_registry(path)}[source_id]


def _portfolio(path: Path, source_id: str):
    return {entry.source_id: entry for entry in load_source_portfolio(path)}[source_id]

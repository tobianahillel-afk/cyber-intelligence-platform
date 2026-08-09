from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from cip.adapters.sources.incident_catalogs.sec_registry import SecIncidentTarget
from cip.modules.collection_orchestration.application.phishtank_adapter import PhishTankAdapter
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.collection_orchestration.application.sec_incident_adapter import (
    SecCyberDisclosureAdapter,
)
from cip.modules.incident_intelligence.domain.models import (
    IncidentClaimType,
    IncidentType,
    OrganizationLinkStatus,
)
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)
from cip.modules.threat_telemetry.domain.models import (
    IndicatorState,
    IndicatorType,
    SensorScope,
)

NOW = datetime(2026, 8, 9, 23, 30, tzinfo=UTC)
RETENTION = NOW + timedelta(days=365)
JOB_ID = UUID("00000000-0000-0000-0000-000000000404")
ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000000405")
INCIDENT_REGISTRY = Path("policies/sources.incidents.yml")
TELEMETRY_REGISTRY = Path("policies/sources.threat_telemetry.yml")


def test_sec_without_targets_performs_no_network_and_needs_no_user_agent() -> None:
    adapter = SecCyberDisclosureAdapter(
        _entry(INCIDENT_REGISTRY, "sec-cyber-disclosures"),
        (),
        user_agent=None,
        transport=httpx.MockTransport(_fail_network),
    )

    batch = _collect(adapter)

    assert batch.not_modified is True
    assert batch.incident_claims == ()


def test_sec_enabled_target_requires_declared_user_agent_before_network() -> None:
    adapter = SecCyberDisclosureAdapter(
        _entry(INCIDENT_REGISTRY, "sec-cyber-disclosures"),
        (_sec_target(),),
        user_agent=None,
        transport=httpx.MockTransport(_fail_network),
    )

    with pytest.raises(AdapterExecutionError) as error:
        _collect(adapter)

    assert error.value.error_code == "provider_not_configured"
    assert error.value.retryable is False


def test_sec_maps_only_non_amended_item_105_as_official_confirmation() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _json_response(
            {
                "cik": 320193,
                "name": "Example Issuer",
                "filings": {
                    "recent": {
                        "accessionNumber": [
                            "0000320193-26-000010",
                            "0000320193-26-000009",
                            "0000320193-26-000008",
                        ],
                        "filingDate": ["2026-08-09", "2026-08-08", "2026-08-07"],
                        "reportDate": ["2026-08-09", "2026-08-08", "2026-08-07"],
                        "acceptanceDateTime": [
                            "2026-08-09T20:00:00Z",
                            "2026-08-08T20:00:00Z",
                            "2026-08-07T20:00:00Z",
                        ],
                        "form": ["8-K", "8-K/A", "10-Q"],
                        "items": ["1.05,9.01", "1.05", "1.05"],
                    }
                },
            }
        )

    adapter = SecCyberDisclosureAdapter(
        _entry(INCIDENT_REGISTRY, "sec-cyber-disclosures"),
        (_sec_target(),),
        user_agent="CIP security-research contact@example.com",
        transport=httpx.MockTransport(handler),
    )
    batch = _collect(adapter)

    assert len(requests) == 1
    assert requests[0].url.host == "data.sec.gov"
    assert requests[0].url.path == "/submissions/CIK0000320193.json"
    assert requests[0].headers["User-Agent"] == "CIP security-research contact@example.com"
    assert len(batch.observations) == 1
    assert len(batch.incident_claims) == 1
    claim = batch.incident_claims[0]
    assert claim.claim_type is IncidentClaimType.COMPANY_CONFIRMATION
    assert claim.incident_type is IncidentType.UNKNOWN
    assert claim.organization_id == ORGANIZATION_ID
    assert claim.organization_link_status is OrganizationLinkStatus.EXACT
    assert claim.occurrence_start_at is None
    assert claim.confirmed_at == datetime(2026, 8, 9, 20, 0, tzinfo=UTC)
    assert claim.is_official_confirmation is True


def test_sec_rejects_mismatched_response_cik() -> None:
    adapter = SecCyberDisclosureAdapter(
        _entry(INCIDENT_REGISTRY, "sec-cyber-disclosures"),
        (_sec_target(),),
        user_agent="CIP contact@example.com",
        transport=httpx.MockTransport(
            lambda _request: _json_response(
                {
                    "cik": 1,
                    "name": "Wrong issuer",
                    "filings": {"recent": _empty_recent()},
                }
            )
        ),
    )

    with pytest.raises(AdapterExecutionError) as error:
        _collect(adapter)

    assert error.value.error_code == "source_identity_mismatch"


def test_phishtank_requires_key_before_network() -> None:
    adapter = PhishTankAdapter(
        _entry(TELEMETRY_REGISTRY, "phishtank-verified-online"),
        token_provider=lambda: None,
        user_agent="CIP contact@example.com",
        transport=httpx.MockTransport(_fail_network),
    )

    with pytest.raises(AdapterExecutionError) as error:
        _collect(adapter)

    assert error.value.error_code == "provider_not_connected"


def test_phishtank_projects_global_url_telemetry_without_brand_compromise() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _json_response(
            [
                {
                    "phish_id": 101,
                    "phish_detail_url": "https://www.phishtank.com/phish_detail.php?phish_id=101",
                    "url": "https://phish.example.net/login",
                    "submission_time": "2026-08-09T20:00:00Z",
                    "verified": "yes",
                    "verification_time": "2026-08-09T20:05:00Z",
                    "online": "yes",
                    "target": "Example Bank",
                }
            ]
        )

    adapter = PhishTankAdapter(
        _entry(TELEMETRY_REGISTRY, "phishtank-verified-online"),
        token_provider=lambda: "secret-key",
        user_agent="CIP contact@example.com",
        transport=httpx.MockTransport(handler),
    )
    batch = _collect(adapter)

    assert len(requests) == 1
    assert requests[0].url.host == "data.phishtank.com"
    assert "/secret-key/online-valid.json" in requests[0].url.path
    assert requests[0].headers["User-Agent"] == "CIP contact@example.com"
    assert len(batch.observations) == 1
    assert "secret-key" not in batch.observations[0].source_url
    assert len(batch.threat_indicator_snapshots) == 1
    snapshot = batch.threat_indicator_snapshots[0]
    assert snapshot.indicator_type is IndicatorType.URL
    assert snapshot.state is IndicatorState.MALICIOUS
    assert snapshot.sensor_scope is SensorScope.PROVIDER_AGGREGATE
    assert snapshot.direct_validation_performed is False
    assert snapshot.relations == ()
    assert snapshot.expires_at == NOW + timedelta(hours=2)


def _collect(adapter: SecCyberDisclosureAdapter | PhishTankAdapter):
    return adapter.collect(
        collection_job_id=JOB_ID,
        checkpoint_payload=None,
        collected_at=NOW,
        retention_until=RETENTION,
    )


def _entry(path: Path, source_id: str) -> SourceRegistryEntry:
    return {entry.policy.id: entry for entry in load_source_registry(path)}[source_id]


def _sec_target() -> SecIncidentTarget:
    return SecIncidentTarget(
        target_id="issuer-example",
        organization_id=ORGANIZATION_ID,
        cik="0000320193",
        enabled=True,
    )


def _empty_recent() -> dict[str, list[object]]:
    return {
        "accessionNumber": [],
        "filingDate": [],
        "reportDate": [],
        "acceptanceDateTime": [],
        "form": [],
        "items": [],
    }


def _json_response(payload: object) -> httpx.Response:
    return httpx.Response(
        200,
        headers={"content-type": "application/json"},
        content=json.dumps(payload).encode("utf-8"),
    )


def _fail_network(_request: httpx.Request) -> httpx.Response:
    raise AssertionError("network must not run")

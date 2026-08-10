from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from cip.modules.source_activation.domain.audit import audit_inventory
from cip.modules.source_activation.domain.models import (
    ActivationDisposition,
    ActivationRecord,
    ActivationStage,
)
from cip.modules.source_activation.infrastructure.inventory import load_activation_inventory

ACTIVATION_PATH = Path("policies/source_activation.yml")
MATRIX_PATH = Path("docs/source_activation/SOURCE_COVERAGE_MATRIX.md")
RDAP_TARGETS_PATH = Path("policies/rdap_targets.yml")
DEVELOPER_TARGETS_PATH = Path("policies/developer_ecosystem_targets.yml")
PUBLIC_WEB_TARGETS_PATH = Path("policies/public_web_targets.yml")

EXECUTABLE_STAGES = {
    ActivationStage.CATALOGUED,
    ActivationStage.REVIEWED,
    ActivationStage.MAPPED,
    ActivationStage.ADAPTER_PRESENT,
    ActivationStage.AUTHORIZED,
    ActivationStage.EXECUTABLE,
}

SA01_EXECUTABLE = {
    "cve-org-services",
    "nvd-vulnerabilities",
    "first-epss",
    "osv-api",
    "github-global-advisories",
    "circl-vulnerability-lookup",
}
SA02_EXECUTABLE = {"brave-search-api", "internet-archive-cdx"}
SA03_EXECUTABLE = {"cloudflare-doh", "certspotter-ct"}
SA04_EXECUTABLE = {"sec-cyber-disclosures", "phishtank-verified-online"}
B1_B2_EXECUTABLE = {
    "iana-rdap-public",
    "github-public-org-repositories",
    "gitlab-public-group-projects",
    "pypi-public-package-metadata",
    "npm-public-package-metadata",
    "maven-central-public-metadata",
}
B4_TERMINAL = {
    "censys-platform-passive",
    "shodan-passive-data",
    "securitytrails-passive-data",
    "urlscan-passive-search",
    "wappalyzer-technographics",
    "builtwith-technographics",
}
FUTURE_LICENSED_PASSIVE = {
    "licensed-passive-dns",
    "licensed-certificate-telemetry",
    "licensed-passive-exposure",
    "licensed-technographic-observations",
    "licensed-cloud-asset-observations",
}
MATRIX_LABELS = {
    "iana-rdap-public": "IANA-bootstrapped public RDAP",
    "github-public-org-repositories": "GitHub public organization repositories",
    "gitlab-public-group-projects": "GitLab public group projects",
    "pypi-public-package-metadata": "PyPI public package metadata",
    "npm-public-package-metadata": "npm public package metadata",
    "maven-central-public-metadata": "Maven Central public artifact metadata",
    "censys-platform-passive": "`censys-platform-passive`",
    "shodan-passive-data": "`shodan-passive-data`",
    "securitytrails-passive-data": "`securitytrails-passive-data`",
    "urlscan-passive-search": "`urlscan-passive-search`",
    "wappalyzer-technographics": "`wappalyzer-technographics`",
    "builtwith-technographics": "`builtwith-technographics`",
    "licensed-passive-dns": "Licensed passive DNS",
    "licensed-certificate-telemetry": "Licensed certificate telemetry",
    "licensed-passive-exposure": "Licensed passive exposure",
    "licensed-technographic-observations": "Licensed technography",
    "licensed-cloud-asset-observations": "Licensed cloud-asset observations",
}


def test_priority_b_inventory_is_structurally_valid() -> None:
    records = load_activation_inventory(ACTIVATION_PATH)

    audit = audit_inventory(records)

    assert audit.total == len(records)


def test_sa00_through_sa04_regression_state_is_explicit() -> None:
    records = _records()
    osint_import = records["osint-framework-import"]

    assert osint_import.disposition is ActivationDisposition.PLANNED
    assert osint_import.activation_wave == "SA-00"
    assert {
        ActivationStage.CATALOGUED,
        ActivationStage.REVIEWED,
    } <= osint_import.stages
    assert ActivationStage.EXECUTABLE not in osint_import.stages

    for source_id in SA01_EXECUTABLE:
        _assert_executable(records[source_id], wave="SA-01")
    for source_id in SA02_EXECUTABLE:
        _assert_executable(records[source_id], wave="SA-02")
    for source_id in SA03_EXECUTABLE:
        _assert_executable(records[source_id], wave="SA-03")
    for source_id in SA04_EXECUTABLE:
        _assert_executable(records[source_id], wave="SA-04")


def test_b1_b2_exact_sources_are_active_executable_and_target_bound() -> None:
    records = _records()

    for source_id in B1_B2_EXECUTABLE:
        _assert_executable(records[source_id], wave="Priority-B")

    assert _yaml(RDAP_TARGETS_PATH)["targets"] == []
    assert _yaml(DEVELOPER_TARGETS_PATH)["targets"] == []


def test_b3_capability_does_not_fake_authorize_example_target() -> None:
    records = _records()
    record = records["public-web-example-fr-organization"]
    target = _yaml(PUBLIC_WEB_TARGETS_PATH)["targets"][0]
    matrix = MATRIX_PATH.read_text(encoding="utf-8")

    assert record.disposition is ActivationDisposition.PLANNED
    assert record.activation_wave == "SA-02"
    assert ActivationStage.ADAPTER_PRESENT in record.stages
    assert ActivationStage.AUTHORIZED not in record.stages
    assert ActivationStage.EXECUTABLE not in record.stages
    assert target["id"] == record.source_id
    assert target["enabled"] is False
    assert target["authorization"]["document_reference"] is None
    assert target["authorization"]["reviewed_at"] is None
    assert "Priority B-3 public web/feed/document completion boundary" in matrix


def test_b4_exact_providers_are_terminal_owned_fail_closed_records() -> None:
    records = _records()
    forbidden = {
        ActivationStage.ADAPTER_PRESENT,
        ActivationStage.AUTHORIZED,
        ActivationStage.EXECUTABLE,
        ActivationStage.SCHEDULED,
        ActivationStage.LIVE_TESTED,
    }

    for source_id in B4_TERMINAL:
        record = records[source_id]
        assert record.disposition is ActivationDisposition.BLOCKED
        assert record.activation_wave == "SA-07"
        assert record.reason is not None
        assert record.reason.strip()
        assert record.is_resolved is True
        assert record.stages.isdisjoint(forbidden)


def test_future_licensed_passive_families_are_terminal_sa07_dependencies() -> None:
    records = _records()
    forbidden = {
        ActivationStage.ADAPTER_PRESENT,
        ActivationStage.AUTHORIZED,
        ActivationStage.EXECUTABLE,
        ActivationStage.SCHEDULED,
        ActivationStage.LIVE_TESTED,
    }

    for source_id in FUTURE_LICENSED_PASSIVE:
        record = records[source_id]
        assert record.disposition is ActivationDisposition.BLOCKED
        assert record.activation_wave == "SA-07"
        assert ActivationStage.MAPPED in record.stages
        assert record.reason is not None
        assert record.reason.strip()
        assert record.is_resolved is True
        assert record.stages.isdisjoint(forbidden)


def test_activation_truth_and_matrix_agree_for_priority_b_scope() -> None:
    records = _records()
    matrix = MATRIX_PATH.read_text(encoding="utf-8")
    exact_ids = B1_B2_EXECUTABLE | B4_TERMINAL | FUTURE_LICENSED_PASSIVE

    assert records.keys() >= exact_ids
    assert MATRIX_LABELS.keys() == exact_ids
    for source_id, label in MATRIX_LABELS.items():
        assert source_id in records
        assert label in matrix


def _assert_executable(record: ActivationRecord, *, wave: str) -> None:
    assert record.disposition is ActivationDisposition.ACTIVE
    assert record.activation_wave == wave
    assert record.stages >= EXECUTABLE_STAGES


def _records() -> dict[str, ActivationRecord]:
    return {record.source_id: record for record in load_activation_inventory(ACTIVATION_PATH)}


def _yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload

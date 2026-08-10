from __future__ import annotations

from pathlib import Path

from cip.modules.source_activation.domain.models import (
    ActivationDisposition,
    ActivationStage,
)
from cip.modules.source_activation.infrastructure.inventory import load_activation_inventory

ACTIVATION_PATH = Path("policies/source_activation.yml")
DECISION_PATH = Path("docs/source_activation/PRIORITY_B_04_PASSIVE_PROVIDER_DECISIONS.md")
MATRIX_PATH = Path("docs/source_activation/SOURCE_COVERAGE_MATRIX.md")

PROVIDER_IDS = {
    "censys-platform-passive",
    "shodan-passive-data",
    "securitytrails-passive-data",
    "urlscan-passive-search",
    "wappalyzer-technographics",
    "builtwith-technographics",
}

FORBIDDEN_STAGES = {
    ActivationStage.ADAPTER_PRESENT,
    ActivationStage.AUTHORIZED,
    ActivationStage.EXECUTABLE,
    ActivationStage.SCHEDULED,
    ActivationStage.LIVE_TESTED,
}


def test_priority_b4_named_providers_are_terminal_fail_closed_sa07_dependencies() -> None:
    records = {record.source_id: record for record in load_activation_inventory(ACTIVATION_PATH)}

    assert records.keys() >= PROVIDER_IDS
    for source_id in PROVIDER_IDS:
        record = records[source_id]
        assert record.disposition is ActivationDisposition.BLOCKED
        assert record.activation_wave == "SA-07"
        assert record.requires_schedule is False
        assert record.reason is not None
        assert record.reason.strip()
        assert record.is_resolved is True
        assert {
            ActivationStage.CATALOGUED,
            ActivationStage.REVIEWED,
            ActivationStage.MAPPED,
        } <= record.stages
        assert record.stages.isdisjoint(FORBIDDEN_STAGES)


def test_priority_b4_decision_record_and_matrix_cover_every_named_provider() -> None:
    decision = DECISION_PATH.read_text(encoding="utf-8")
    matrix = MATRIX_PATH.read_text(encoding="utf-8")

    for source_id in PROVIDER_IDS:
        assert f"`{source_id}`" in decision
        assert f"`{source_id}`" in matrix


def test_priority_b4_does_not_create_provider_runtime_authority() -> None:
    repository_root = Path("src/cip/adapters/sources")
    provider_runtime_names = {
        "censys",
        "shodan",
        "securitytrails",
        "urlscan",
        "wappalyzer",
        "builtwith",
    }

    paths = {path.name.lower() for path in repository_root.rglob("*.py")}
    for provider_name in provider_runtime_names:
        assert all(provider_name not in filename for filename in paths)

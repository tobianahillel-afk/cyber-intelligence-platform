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
AUDIT_PATH = Path("docs/source_activation/SA_10_FINAL_SOURCE_COMPLETENESS_AUDIT.md")
PUBLIC_WEB_TARGETS_PATH = Path("policies/public_web_targets.yml")

TERMINALIZED = {
    "recherche-entreprises": ActivationDisposition.MANUAL,
    "gleif": ActivationDisposition.MANUAL,
    "bodacc-identity": ActivationDisposition.MANUAL,
    "osint-framework-import": ActivationDisposition.MANUAL,
    "public-web-example-fr-organization": ActivationDisposition.NOT_RELEVANT,
    "official-company-incident-disclosures": ActivationDisposition.NOT_RELEVANT,
    "regulator-cert-incident-notices": ActivationDisposition.NOT_RELEVANT,
    "official-vendor-psirt": ActivationDisposition.NOT_RELEVANT,
    "official-linux-security-advisories": ActivationDisposition.NOT_RELEVANT,
    "official-package-security-advisories": ActivationDisposition.NOT_RELEVANT,
}
TERMINAL_NON_EXECUTABLE = {
    ActivationDisposition.MANUAL,
    ActivationDisposition.BLOCKED,
    ActivationDisposition.REPLACED,
    ActivationDisposition.DUPLICATE,
    ActivationDisposition.NOT_RELEVANT,
}


def test_sa10_has_no_planned_activation_records() -> None:
    records = _records()

    assert all(record.disposition is not ActivationDisposition.PLANNED for record in records)


def test_sa10_terminalizes_remaining_records_without_execution_authority() -> None:
    records = {record.source_id: record for record in _records()}

    for source_id, disposition in TERMINALIZED.items():
        record = records[source_id]
        assert record.disposition is disposition
        assert record.reason
        assert record.is_resolved
        assert ActivationStage.AUTHORIZED not in record.stages
        assert ActivationStage.EXECUTABLE not in record.stages
        assert ActivationStage.LIVE_TESTED not in record.stages


def test_every_terminal_non_executable_record_is_resolved_with_reason() -> None:
    for record in _records():
        if record.disposition in TERMINAL_NON_EXECUTABLE:
            assert record.reason
            assert record.is_resolved


def test_sa10_preserves_real_live_validation_as_open_gate() -> None:
    records = _records()
    audit = audit_inventory(records)
    active_incomplete = tuple(
        sorted(
            record.source_id
            for record in records
            if record.disposition is ActivationDisposition.ACTIVE
            and not record.is_fully_integrated
        )
    )

    assert active_incomplete
    assert audit.unresolved == active_incomplete
    assert audit.complete is False
    for record in records:
        if record.source_id in active_incomplete:
            assert record.missing_integration_stages


def test_real_live_proofs_extend_fully_integrated_source_set() -> None:
    integrated = {
        record.source_id for record in _records() if record.is_fully_integrated
    }

    assert integrated >= {
        "reference-synthetic",
        "ashby-job-board",
        "recruitee-careers-site",
    }
    assert "teamtailor-public-jobs" not in integrated


def test_public_web_sample_remains_disabled_after_terminalization() -> None:
    payload = _yaml(PUBLIC_WEB_TARGETS_PATH)
    target = payload["targets"][0]

    assert target["id"] == "public-web-example-fr-organization"
    assert target["enabled"] is False
    assert target["authorization"]["document_reference"] is None
    assert target["authorization"]["reviewed_at"] is None


def test_sa10_audit_and_matrix_cover_terminalized_sources_and_open_live_gate() -> None:
    audit_text = AUDIT_PATH.read_text(encoding="utf-8")
    matrix = MATRIX_PATH.read_text(encoding="utf-8")

    for source_id in TERMINALIZED:
        assert f"`{source_id}`" in audit_text
        assert f"`{source_id}`" in matrix
    assert "Controlled live validation: still open" in audit_text
    assert "SA-10 final source completeness" in matrix


def _records() -> list[ActivationRecord]:
    return list(load_activation_inventory(ACTIVATION_PATH))


def _yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload

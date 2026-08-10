from pathlib import Path

from cip.modules.source_activation.domain.models import (
    ActivationDisposition,
    ActivationRecord,
    ActivationStage,
)
from cip.modules.source_activation.infrastructure.inventory import load_activation_inventory

ACTIVATION_PATH = Path("policies/source_activation.yml")
DECISIONS_PATH = Path("docs/source_activation/SA_07_LICENSED_PREMIUM_PROVIDER_DECISIONS.md")
MATRIX_PATH = Path("docs/source_activation/SOURCE_COVERAGE_MATRIX.md")

FORBIDDEN_BLOCKED_STAGES = {
    ActivationStage.ADAPTER_PRESENT,
    ActivationStage.AUTHORIZED,
    ActivationStage.EXECUTABLE,
    ActivationStage.SCHEDULED,
    ActivationStage.LIVE_TESTED,
}


def test_every_sa07_record_is_terminal_blocked_with_reason() -> None:
    records = _sa07_records()
    assert records
    assert len(records) == 21
    for record in records:
        assert record.disposition is ActivationDisposition.BLOCKED
        assert record.reason
        assert record.is_resolved
        assert record.stages.isdisjoint(FORBIDDEN_BLOCKED_STAGES)


def test_sa07_has_no_planned_records() -> None:
    assert all(
        record.disposition is not ActivationDisposition.PLANNED
        for record in _sa07_records()
    )


def test_sa07_decision_record_and_matrix_cover_every_source_id() -> None:
    decisions = DECISIONS_PATH.read_text(encoding="utf-8")
    matrix = MATRIX_PATH.read_text(encoding="utf-8")
    for record in _sa07_records():
        assert f"`{record.source_id}`" in decisions
        assert f"`{record.source_id}`" in matrix


def _sa07_records() -> list[ActivationRecord]:
    return [
        record
        for record in load_activation_inventory(ACTIVATION_PATH)
        if record.activation_wave == "SA-07"
    ]

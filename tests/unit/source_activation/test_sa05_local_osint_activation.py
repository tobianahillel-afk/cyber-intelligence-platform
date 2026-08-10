from __future__ import annotations

from pathlib import Path

from cip.modules.source_activation.domain.models import (
    ActivationDisposition,
    ActivationRecord,
    ActivationStage,
)
from cip.modules.source_activation.infrastructure.inventory import load_activation_inventory

ACTIVATION_PATH = Path("policies/source_activation.yml")
TARGETS_PATH = Path("policies/sherlock_targets.yml")
DOC_PATH = Path("docs/source_activation/SA_05_GOVERNED_LOCAL_OSINT.md")

SHERLOCK = "sherlock-local"
BLOCKED_FRAMEWORKS = {
    "amass-local",
    "theharvester-local",
    "spiderfoot-local",
    "recon-ng-local",
}
MANUAL_TOOLS = {SHERLOCK, "maltego-local"}
FORBIDDEN_RUNTIME_STAGES = {
    ActivationStage.AUTHORIZED,
    ActivationStage.EXECUTABLE,
    ActivationStage.SCHEDULED,
    ActivationStage.LIVE_TESTED,
}


def test_sa05_sherlock_is_manual_adapter_present_and_fail_closed() -> None:
    records = _records()
    record = records[SHERLOCK]

    assert record.disposition is ActivationDisposition.MANUAL
    assert record.activation_wave == "SA-05"
    assert record.requires_schedule is False
    assert record.reason
    assert record.is_resolved is True
    assert record.stages >= {
        ActivationStage.CATALOGUED,
        ActivationStage.REVIEWED,
        ActivationStage.MAPPED,
        ActivationStage.ADAPTER_PRESENT,
    }
    assert record.stages.isdisjoint(FORBIDDEN_RUNTIME_STAGES)
    assert TARGETS_PATH.read_text(encoding="utf-8") == "version: 1\ntargets: []\n"


def test_sa05_multisource_frameworks_never_gain_blanket_authority() -> None:
    records = _records()

    for source_id in BLOCKED_FRAMEWORKS:
        record = records[source_id]
        assert record.disposition is ActivationDisposition.BLOCKED
        assert record.activation_wave == "SA-05"
        assert record.reason
        assert record.is_resolved is True
        assert record.stages >= {
            ActivationStage.CATALOGUED,
            ActivationStage.REVIEWED,
            ActivationStage.MAPPED,
        }
        assert record.stages.isdisjoint(FORBIDDEN_RUNTIME_STAGES)


def test_sa05_manual_tools_are_explicit_and_documented() -> None:
    records = _records()
    document = DOC_PATH.read_text(encoding="utf-8")

    assert records["maltego-local"].disposition is ActivationDisposition.MANUAL
    for source_id in MANUAL_TOOLS | BLOCKED_FRAMEWORKS:
        assert source_id in records
    tool_names = (
        "Sherlock",
        "Amass",
        "theHarvester",
        "SpiderFoot",
        "Recon-ng",
        "Maltego",
    )
    for tool_name in tool_names:
        assert tool_name in document


def _records() -> dict[str, ActivationRecord]:
    return {record.source_id: record for record in load_activation_inventory(ACTIVATION_PATH)}

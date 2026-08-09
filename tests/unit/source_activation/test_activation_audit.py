from __future__ import annotations

from dataclasses import replace

import pytest

from cip.modules.source_activation.domain import (
    ActivationDisposition,
    ActivationRecord,
    ActivationStage,
    audit_inventory,
)

ALL_STAGES = frozenset(ActivationStage)


def _record(**overrides: object) -> ActivationRecord:
    values: dict[str, object] = {
        "source_id": "source-a",
        "display_name": "Source A",
        "category": "test",
        "disposition": ActivationDisposition.ACTIVE,
        "stages": ALL_STAGES,
    }
    values.update(overrides)
    return ActivationRecord(**values)  # type: ignore[arg-type]


def test_active_source_requires_every_runtime_stage() -> None:
    complete = _record()
    missing_live = replace(
        complete,
        stages=complete.stages - {ActivationStage.LIVE_TESTED},
    )

    assert complete.is_fully_integrated is True
    assert missing_live.is_fully_integrated is False
    assert missing_live.missing_integration_stages == (ActivationStage.LIVE_TESTED,)


def test_query_only_source_can_be_integrated_without_schedule() -> None:
    stages = ALL_STAGES - {ActivationStage.SCHEDULED}
    record = _record(requires_schedule=False, stages=stages)

    assert record.is_fully_integrated is True


def test_terminal_non_executable_source_requires_reason() -> None:
    with pytest.raises(ValueError, match="require a reason"):
        _record(
            disposition=ActivationDisposition.BLOCKED,
            stages=frozenset({ActivationStage.CATALOGUED}),
            reason=None,
        )


def test_replaced_and_duplicate_sources_require_real_references() -> None:
    source = _record(source_id="replacement")
    replaced = _record(
        source_id="old",
        disposition=ActivationDisposition.REPLACED,
        stages=frozenset({ActivationStage.CATALOGUED}),
        reason="superseded",
        replacement_source_id="replacement",
    )

    assert audit_inventory((source, replaced)).unresolved == ()

    invalid = replace(replaced, replacement_source_id="missing")
    with pytest.raises(ValueError, match="unknown activation source"):
        audit_inventory((source, invalid))


def test_audit_rejects_duplicate_source_ids() -> None:
    with pytest.raises(ValueError, match="duplicate source activation records"):
        audit_inventory((_record(), _record()))


def test_audit_preserves_unresolved_planned_sources() -> None:
    planned = _record(
        source_id="planned",
        disposition=ActivationDisposition.PLANNED,
        stages=frozenset({ActivationStage.CATALOGUED, ActivationStage.REVIEWED}),
    )

    audit = audit_inventory((_record(), planned))

    assert audit.total == 2
    assert audit.fully_integrated == 1
    assert audit.resolved_non_executable == 0
    assert audit.unresolved == ("planned",)
    assert audit.complete is False

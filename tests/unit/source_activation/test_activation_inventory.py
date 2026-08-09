from __future__ import annotations

from pathlib import Path

import pytest

from cip.modules.source_activation.domain import ActivationStage, audit_inventory
from cip.modules.source_activation.infrastructure import load_activation_inventory

ROOT = Path(__file__).parents[3]
INVENTORY = ROOT / "policies" / "source_activation.yml"


def test_checked_in_activation_inventory_is_valid_and_auditable() -> None:
    records = load_activation_inventory(INVENTORY)
    audit = audit_inventory(records)

    assert len(records) >= 20
    assert audit.total == len(records)
    assert "nvd-vulnerabilities" in audit.unresolved
    assert "brixhub" not in audit.unresolved


def test_inventory_does_not_claim_legacy_network_sources_are_live_tested() -> None:
    records = {record.source_id: record for record in load_activation_inventory(INVENTORY)}

    for source_id in (
        "cisa-kev",
        "ted-search",
        "boamp",
        "greenhouse-job-board",
        "lever-job-board",
        "smartrecruiters-job-board",
    ):
        assert ActivationStage.LIVE_TESTED not in records[source_id].stages
        assert records[source_id].is_fully_integrated is False


def test_loader_rejects_unknown_inventory_version(tmp_path: Path) -> None:
    path = tmp_path / "activation.yml"
    path.write_text("version: 2\nsources: []\n", encoding="utf-8")

    with pytest.raises(ValueError, match="version: 1"):
        load_activation_inventory(path)

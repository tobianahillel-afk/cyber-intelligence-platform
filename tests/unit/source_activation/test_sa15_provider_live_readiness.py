from __future__ import annotations

from pathlib import Path

import yaml

from cip.modules.source_activation.domain.models import ActivationStage
from cip.modules.source_activation.infrastructure import load_activation_inventory
from cip.shared.config.settings import Settings


_PROVIDER_IDS = (
    "brave-search-api",
    "mojeek-web-search-metadata",
    "patentsview-patent-metadata",
)


def test_credentialed_sa15_providers_are_executable_but_not_falsely_live() -> None:
    records = {
        record.source_id: record
        for record in load_activation_inventory(Settings().source_activation_path)
    }

    for source_id in _PROVIDER_IDS:
        record = records[source_id]
        assert ActivationStage.ADAPTER_PRESENT in record.stages
        assert ActivationStage.AUTHORIZED in record.stages
        assert ActivationStage.EXECUTABLE in record.stages
        assert ActivationStage.LIVE_TESTED not in record.stages
        assert record.is_fully_integrated is False


def test_mojeek_checked_in_storage_entitlement_remains_fail_closed() -> None:
    payload = yaml.safe_load(
        Path("policies/mojeek_search_entitlement.yml").read_text(encoding="utf-8")
    )
    entitlement = payload["entitlement"]

    assert entitlement["durable_storage_authorized"] is False
    assert entitlement["plan"] == "unprovisioned"
    assert entitlement["evidence_reference"] is None


def test_patentsview_has_no_checked_in_production_target() -> None:
    payload = yaml.safe_load(
        Path("policies/patentsview_patent_targets.yml").read_text(encoding="utf-8")
    )

    assert payload["targets"] == []


def test_manual_live_workflow_references_only_production_runners_and_secret_names() -> None:
    workflow = Path(".github/workflows/sa15-provider-live-validation.yml").read_text(
        encoding="utf-8"
    )

    for script_name in (
        "live_validate_sa15_brave.py",
        "live_validate_sa15_mojeek.py",
        "live_validate_sa15_patentsview.py",
    ):
        assert f"python scripts/{script_name}" in workflow
    for secret_name in (
        "BRAVE_SEARCH_API_TOKEN",
        "MOJEEK_API_KEY",
        "PATENTSVIEW_API_KEY",
    ):
        assert f"secrets.{secret_name}" in workflow
    assert "live_tested" not in workflow

from pathlib import Path
from textwrap import dedent

import pytest

from cip.modules.collection_orchestration.infrastructure.schedule_bundle import (
    load_collection_schedule_bundle,
)
from cip.modules.provider_onboarding.infrastructure.registry import load_provider_profiles
from cip.modules.source_activation.domain.models import (
    ActivationDisposition,
    ActivationStage,
)
from cip.modules.source_activation.infrastructure.inventory import load_activation_inventory
from cip.modules.source_portfolio.infrastructure.registry_bundle import (
    load_source_portfolio_bundle,
)

ACTIVATION_PATH = Path("policies/source_activation.yml")
PORTFOLIO_PATH = Path("policies/source_portfolio.ats_expansion.yml")
SCHEDULE_PATH = Path("policies/collection_schedules.ats_expansion.yml")
ONBOARDING_PATH = Path("policies/provider_onboarding.yml")
LIVE_WORKFLOW_PATH = Path(".github/workflows/sa13-live-validation.yml")


def test_sa13_ashby_and_recruitee_are_real_live_integrations() -> None:
    records = {record.source_id: record for record in load_activation_inventory(ACTIVATION_PATH)}

    for source_id in ("ashby-job-board", "recruitee-careers-site"):
        record = records[source_id]
        assert record.disposition is ActivationDisposition.ACTIVE
        assert record.activation_wave == "SA-13"
        assert record.is_fully_integrated
        assert {
            ActivationStage.ADAPTER_PRESENT,
            ActivationStage.AUTHORIZED,
            ActivationStage.EXECUTABLE,
            ActivationStage.SCHEDULED,
            ActivationStage.LIVE_TESTED,
        } <= record.stages


def test_sa13_teamtailor_stays_truthfully_incomplete_without_account_token() -> None:
    records = {record.source_id: record for record in load_activation_inventory(ACTIVATION_PATH)}
    record = records["teamtailor-public-jobs"]

    assert record.disposition is ActivationDisposition.ACTIVE
    assert record.activation_wave == "SA-13"
    assert ActivationStage.ADAPTER_PRESENT in record.stages
    assert ActivationStage.AUTHORIZED in record.stages
    assert ActivationStage.EXECUTABLE not in record.stages
    assert ActivationStage.SCHEDULED not in record.stages
    assert ActivationStage.LIVE_TESTED not in record.stages
    assert record.is_fully_integrated is False


def test_sa13_portfolio_and_schedules_match_runtime_state() -> None:
    portfolio = {
        entry.source_id: entry
        for entry in load_source_portfolio_bundle(PORTFOLIO_PATH)
    }
    schedules = {
        schedule.source_id: schedule
        for schedule in load_collection_schedule_bundle(SCHEDULE_PATH)
    }

    assert portfolio["ashby-job-board"].executable is True
    assert portfolio["recruitee-careers-site"].executable is True
    assert portfolio["teamtailor-public-jobs"].executable is False
    assert schedules["ashby-job-board"].enabled is True
    assert schedules["recruitee-careers-site"].enabled is True
    assert schedules["teamtailor-public-jobs"].enabled is False


def test_sa13_provider_onboarding_uses_only_required_authentication() -> None:
    profiles = {
        profile.source_id: profile for profile in load_provider_profiles(ONBOARDING_PATH)
    }

    assert profiles["ashby-job-board"].required_secret_names == ()
    assert profiles["recruitee-careers-site"].required_secret_names == ()
    assert profiles["teamtailor-public-jobs"].required_secret_names == ("api_token",)
    assert profiles["teamtailor-public-jobs"].automatic_onboarding is False


def test_sa13_live_validation_executes_real_adapters() -> None:
    workflow = LIVE_WORKFLOW_PATH.read_text(encoding="utf-8")
    script = Path("scripts/live_validate_sa13.py").read_text(encoding="utf-8")

    assert "Controlled Ashby and Recruitee live validation" in workflow
    assert "python scripts/live_validate_sa13.py" in workflow
    assert "AshbyAdapter(" in script
    assert "RecruiteeAdapter(" in script
    assert "ashby_count < 1" in script
    assert "recruitee_count < 1" in script


def test_activation_inventory_bundle_rejects_duplicate_ids(tmp_path: Path) -> None:
    base = tmp_path / "source_activation.yml"
    base.write_text(
        dedent(
            """
            version: 1
            sources:
              - source_id: duplicate
                display_name: Duplicate
                category: test
                disposition: active
                requires_schedule: false
                stages: [catalogued]
            """
        ),
        encoding="utf-8",
    )
    (tmp_path / "source_activation.extra.yml").write_text(
        dedent(
            """
            version: 1
            sources:
              - source_id: duplicate
                display_name: Duplicate Again
                category: test
                disposition: active
                requires_schedule: false
                stages: [catalogued]
            """
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate source activation id"):
        load_activation_inventory(base)

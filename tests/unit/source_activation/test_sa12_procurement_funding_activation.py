from pathlib import Path

from cip.modules.collection_orchestration.infrastructure.schedule_bundle import (
    load_collection_schedule_bundle,
)
from cip.modules.source_activation.domain.models import (
    ActivationDisposition,
    ActivationStage,
)
from cip.modules.source_activation.infrastructure.inventory import load_activation_inventory
from cip.modules.source_governance.domain.models import SourceStatus
from cip.modules.source_governance.infrastructure.registry import load_source_registry
from cip.modules.source_portfolio.infrastructure.registry_bundle import (
    load_source_portfolio_bundle,
)

ACTIVATION_PATH = Path("policies/source_activation.yml")
POLICY_PATH = Path("policies/sources.procurement_funding.yml")
PORTFOLIO_PATH = Path("policies/source_portfolio.procurement_funding.yml")
SCHEDULE_PATH = Path("policies/collection_schedules.procurement_funding.yml")
LIVE_WORKFLOW_PATH = Path(".github/workflows/sa12-live-validation.yml")
LIVE_SCRIPT_PATH = Path("scripts/live_validate_sa12.py")


def test_sa12_providers_are_real_live_integrations() -> None:
    records = {record.source_id: record for record in load_activation_inventory(ACTIVATION_PATH)}

    for source_id in (
        "place-awards",
        "ademe-financial-aid",
        "cordis-eu-funded-projects",
    ):
        record = records[source_id]
        assert record.disposition is ActivationDisposition.ACTIVE
        assert record.activation_wave == "SA-12"
        assert record.is_fully_integrated
        assert {
            ActivationStage.ADAPTER_PRESENT,
            ActivationStage.AUTHORIZED,
            ActivationStage.EXECUTABLE,
            ActivationStage.SCHEDULED,
            ActivationStage.LIVE_TESTED,
        } <= record.stages


def test_sa12_source_governance_is_enabled_and_provider_specific() -> None:
    entries = {entry.policy.id: entry for entry in load_source_registry(POLICY_PATH)}

    place = entries["place-awards"]
    assert place.policy.status is SourceStatus.ENABLED
    assert place.authorization.automated_collection_allowed
    assert place.authorization.approved_hosts == frozenset({"data.economie.gouv.fr"})

    ademe = entries["ademe-financial-aid"]
    assert ademe.policy.status is SourceStatus.ENABLED
    assert ademe.authorization.automated_collection_allowed
    assert ademe.authorization.approved_hosts == frozenset({"data.ademe.fr"})

    cordis = entries["cordis-eu-funded-projects"]
    assert cordis.policy.status is SourceStatus.ENABLED
    assert cordis.authorization.automated_collection_allowed
    assert cordis.authorization.approved_hosts == frozenset({"cordis.europa.eu"})
    assert cordis.authorization.approved_path_prefixes == (
        "/data/cordis-HORIZONprojects-csv.zip",
    )


def test_sa12_portfolio_and_schedules_are_executable() -> None:
    portfolio = {
        entry.source_id: entry
        for entry in load_source_portfolio_bundle(PORTFOLIO_PATH)
    }
    schedules = {
        schedule.source_id: schedule
        for schedule in load_collection_schedule_bundle(SCHEDULE_PATH)
    }

    expected_adapters = {
        "place-awards": "place-open-data-awards-api",
        "ademe-financial-aid": "ademe-data-fair-financial-aid-api",
        "cordis-eu-funded-projects": "cordis-horizon-bulk-csv",
    }
    for source_id, adapter_id in expected_adapters.items():
        assert portfolio[source_id].executable is True
        assert portfolio[source_id].adapter is not None
        assert portfolio[source_id].adapter.adapter_id == adapter_id
        assert schedules[source_id].enabled is True


def test_sa12_live_gate_executes_production_adapters_and_requires_real_data() -> None:
    workflow = LIVE_WORKFLOW_PATH.read_text(encoding="utf-8")
    script = LIVE_SCRIPT_PATH.read_text(encoding="utf-8")

    assert "Controlled PLACE, ADEME and CORDIS live validation" in workflow
    assert "python scripts/live_validate_sa12.py" in workflow
    assert "PlaceAwardsAdapter(" in script
    assert "AdemeFundingAdapter(" in script
    assert "CordisFundingAdapter(" in script
    assert "place_count < 1" in script
    assert "ademe_count < 1" in script
    assert "cordis_count < 1" in script
    assert "place_batch.procurement_projections" in script
    assert "ademe_batch.corporate_change_claims" in script
    assert "cordis_batch.corporate_change_claims" in script
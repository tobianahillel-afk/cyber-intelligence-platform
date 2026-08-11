from pathlib import Path

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
POLICY_PATH = Path("policies/sources.company_identity_expansion.yml")
PORTFOLIO_PATH = Path("policies/source_portfolio.company_identity_expansion.yml")
LIVE_WORKFLOW_PATH = Path(".github/workflows/sa11-live-validation.yml")
LIVE_SCRIPT_PATH = Path("scripts/live_validate_sa11.py")


def test_sa11_brreg_is_fully_integrated_after_live_proof() -> None:
    records = {record.source_id: record for record in load_activation_inventory(ACTIVATION_PATH)}
    record = records["brreg-enhetsregisteret"]

    assert record.disposition is ActivationDisposition.ACTIVE
    assert record.activation_wave == "SA-11"
    assert record.requires_schedule is False
    assert record.is_fully_integrated
    assert {
        ActivationStage.ADAPTER_PRESENT,
        ActivationStage.AUTHORIZED,
        ActivationStage.EXECUTABLE,
        ActivationStage.LIVE_TESTED,
    } <= record.stages
    assert ActivationStage.SCHEDULED not in record.stages


def test_sa11_access_controlled_candidates_remain_fail_closed() -> None:
    records = {record.source_id: record for record in load_activation_inventory(ACTIVATION_PATH)}

    sirene = records["sirene-api"]
    assert sirene.disposition is ActivationDisposition.MANUAL
    assert sirene.reason
    assert ActivationStage.EXECUTABLE not in sirene.stages
    assert ActivationStage.LIVE_TESTED not in sirene.stages

    for source_id in ("inpi-rne", "opencorporates-licensed"):
        record = records[source_id]
        assert record.disposition is ActivationDisposition.BLOCKED
        assert record.reason
        assert ActivationStage.ADAPTER_PRESENT not in record.stages
        assert ActivationStage.EXECUTABLE not in record.stages
        assert ActivationStage.LIVE_TESTED not in record.stages


def test_sa11_brreg_policy_and_portfolio_match_runtime_contract() -> None:
    entries = {entry.policy.id: entry for entry in load_source_registry(POLICY_PATH)}
    entry = entries["brreg-enhetsregisteret"]
    assert entry.policy.status is SourceStatus.ENABLED
    assert entry.authorization.automated_collection_allowed
    assert entry.authorization.approved_hosts == frozenset({"data.brreg.no"})
    assert entry.authorization.approved_path_prefixes == (
        "/enhetsregisteret/api/enheter/",
    )

    portfolio = {
        item.source_id: item
        for item in load_source_portfolio_bundle(PORTFOLIO_PATH)
    }
    source = portfolio["brreg-enhetsregisteret"]
    assert source.executable is True
    assert source.adapter is not None
    assert source.adapter.adapter_id == "brreg-enhetsregisteret-entity"
    assert source.metadata["scheduled_by_default"] is False


def test_sa11_live_gate_executes_production_adapter_without_person_endpoints() -> None:
    workflow = LIVE_WORKFLOW_PATH.read_text(encoding="utf-8")
    script = LIVE_SCRIPT_PATH.read_text(encoding="utf-8")

    assert "Controlled BRREG live validation" in workflow
    assert "python scripts/live_validate_sa11.py" in workflow
    assert "BrregIdentityAdapter(" in script
    assert 'VALIDATION_ORG_NUMBER = "974760673"' in script
    assert "identity_projections" in script
    assert "roller" not in script.casefold()
    assert "maskinporten" not in script.casefold()

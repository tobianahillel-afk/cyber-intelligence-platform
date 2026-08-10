from __future__ import annotations

from pathlib import Path

import yaml

from cip.adapters.sources.passive_infrastructure.rdap_registry import load_rdap_targets
from cip.adapters.sources.passive_infrastructure.registry import (
    load_passive_infrastructure_targets,
)
from cip.modules.collection_orchestration.application.passive_infrastructure_registration import (
    register_passive_infrastructure_adapters,
)
from cip.modules.collection_orchestration.application.rdap_adapter import IanaRdapAdapter
from cip.modules.collection_orchestration.infrastructure.schedule_bundle import (
    load_collection_schedule_bundle,
)
from cip.modules.source_governance.domain.models import SourceStatus
from cip.modules.source_governance.infrastructure.registry import load_source_registry
from cip.modules.source_portfolio.domain.models import CatalogStatus
from cip.modules.source_portfolio.infrastructure.registry import load_source_portfolio

SOURCE_PATH = Path("policies/sources.passive_infrastructure.yml")
PORTFOLIO_PATH = Path("policies/source_portfolio.passive_infrastructure.yml")
SCHEDULE_PATH = Path("policies/collection_schedules.passive_infrastructure.yml")
ACTIVATION_PATH = Path("policies/source_activation.yml")
RDAP_TARGET_PATH = Path("policies/rdap_targets.yml")
PASSIVE_TARGET_PATH = Path("policies/passive_infrastructure_targets.yml")


def test_rdap_governance_portfolio_schedule_and_activation_agree() -> None:
    sources = {entry.policy.id: entry for entry in load_source_registry(SOURCE_PATH)}
    portfolio = {
        entry.source_id: entry for entry in load_source_portfolio(PORTFOLIO_PATH)
    }
    schedules = load_collection_schedule_bundle(SCHEDULE_PATH)
    activation = yaml.safe_load(ACTIVATION_PATH.read_text(encoding="utf-8"))
    activation_by_id = {
        item["source_id"]: item for item in activation["sources"]
    }

    source = sources[IanaRdapAdapter.source_id]
    assert source.policy.status is SourceStatus.ENABLED
    assert source.authorization.automated_collection_allowed is True
    assert source.authorization.approved_hosts == frozenset({"data.iana.org"})

    catalog = portfolio[IanaRdapAdapter.source_id]
    assert catalog.status is CatalogStatus.EXECUTABLE
    assert catalog.executable is True
    assert catalog.adapter is not None
    assert catalog.adapter.adapter_id == IanaRdapAdapter.adapter_id

    rdap_schedules = [
        schedule for schedule in schedules if schedule.source_id == IanaRdapAdapter.source_id
    ]
    assert len(rdap_schedules) == 1
    assert rdap_schedules[0].enabled is False

    truth = activation_by_id[IanaRdapAdapter.source_id]
    assert truth["disposition"] == "active"
    assert truth["requires_schedule"] is False
    assert "executable" in truth["stages"]
    assert "scheduled" not in truth["stages"]
    assert "live_tested" not in truth["stages"]


def test_rdap_adapter_is_registered_even_with_empty_checked_in_targets() -> None:
    entries = load_source_registry(SOURCE_PATH)
    entries_by_id = {entry.policy.id: entry for entry in entries}
    adapters = {}

    register_passive_infrastructure_adapters(
        adapters,
        entries_by_id,
        load_passive_infrastructure_targets(PASSIVE_TARGET_PATH),
        load_rdap_targets(RDAP_TARGET_PATH),
        certspotter_token_provider=lambda: None,
        timeout_seconds=1.0,
    )

    assert (IanaRdapAdapter.source_id, IanaRdapAdapter.adapter_id) in adapters

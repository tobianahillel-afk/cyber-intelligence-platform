from __future__ import annotations

from cip.modules.source_activation.infrastructure import load_activation_inventory
from cip.modules.source_portfolio.infrastructure.registry_bundle import (
    load_source_portfolio_bundle,
)
from cip.shared.config.settings import Settings


def test_every_checked_in_source_portfolio_entry_has_activation_record() -> None:
    settings = Settings()
    portfolio = load_source_portfolio_bundle(
        settings.source_portfolio_path,
        settings.decp_source_portfolio_path,
        settings.public_web_source_portfolio_path,
        settings.vulnerability_source_portfolio_path,
        settings.incident_source_portfolio_path,
        settings.threat_telemetry_source_portfolio_path,
        settings.passive_exposure_source_portfolio_path,
        settings.advisory_source_portfolio_path,
        settings.corporate_change_source_portfolio_path,
        settings.relationship_source_portfolio_path,
        settings.conditional_integration_source_portfolio_path,
    )
    activation = load_activation_inventory(settings.source_activation_path)

    portfolio_ids = {entry.source_id for entry in portfolio}
    activation_ids = {entry.source_id for entry in activation}

    assert portfolio_ids - activation_ids == set()

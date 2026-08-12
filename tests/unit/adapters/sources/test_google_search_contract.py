from __future__ import annotations

import importlib
from pathlib import Path

import pytest


BASE = """version: 1
contract:
  reviewed_at: 2026-08-12
  status: awaiting_eligible_route
  official_references:
    - https://developers.google.com/custom-search/v1/overview
    - https://support.google.com/websearch/answer/86640
  custom_search_api:
    closed_to_new_customers: true
    existing_customer_sunset: 2027-01-01
    api_base_url: https://customsearch.googleapis.com/customsearch/v1
    entitlement_evidence_id: null
    api_key_secret_ref: null
    search_engine_id_secret_ref: null
  browser_route:
    enabled: false
    provider_permission_evidence_id: null
    human_checkpoint_required: true
    captcha_bypass_allowed: false
    anti_bot_bypass_allowed: false
  canonical_replacement:
    approved_source_ids: []
  analyst_route:
    enabled: true
"""


def _google_search_contract():
    return importlib.import_module("cip.adapters.sources.google_search.contract")


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "google.yml"
    path.write_text(content, encoding="utf-8")
    return path


def test_default_contract_fails_closed(tmp_path: Path) -> None:
    module = _google_search_contract()
    contract = module.load_google_search_contract(_write(tmp_path, BASE))

    assert contract.status is module.GoogleSearchContractStatus.AWAITING_ELIGIBLE_ROUTE
    assert contract.automated_route_available is False
    assert contract.analyst_route_enabled is True
    with pytest.raises(module.GoogleSearchRouteUnavailable):
        contract.require_automated_route()


def test_existing_customer_api_requires_all_governed_refs(tmp_path: Path) -> None:
    module = _google_search_contract()
    content = BASE.replace(
        "status: awaiting_eligible_route",
        "status: existing_customer_api",
    ).replace(
        "entitlement_evidence_id: null",
        "entitlement_evidence_id: google-existing-customer-approval-2026",
    )

    with pytest.raises(ValueError, match="API-key refs"):
        module.load_google_search_contract(_write(tmp_path, content))


def test_existing_customer_api_can_be_enabled_with_evidence(tmp_path: Path) -> None:
    module = _google_search_contract()
    content = (
        BASE.replace("status: awaiting_eligible_route", "status: existing_customer_api")
        .replace(
            "entitlement_evidence_id: null",
            "entitlement_evidence_id: google-existing-customer-approval-2026",
        )
        .replace("api_key_secret_ref: null", "api_key_secret_ref: secret://google/api-key")
        .replace(
            "search_engine_id_secret_ref: null",
            "search_engine_id_secret_ref: secret://google/search-engine-id",
        )
    )
    contract = module.load_google_search_contract(_write(tmp_path, content))

    assert contract.automated_route_available is True
    contract.require_automated_route()


def test_browser_route_requires_provider_permission_evidence(tmp_path: Path) -> None:
    module = _google_search_contract()
    content = BASE.replace("enabled: false", "enabled: true", 1)

    with pytest.raises(ValueError, match="provider permission evidence"):
        module.load_google_search_contract(_write(tmp_path, content))


def test_browser_route_rejects_captcha_bypass(tmp_path: Path) -> None:
    module = _google_search_contract()
    content = BASE.replace("captcha_bypass_allowed: false", "captcha_bypass_allowed: true")

    with pytest.raises(ValueError, match="CAPTCHA or anti-bot bypass"):
        module.load_google_search_contract(_write(tmp_path, content))


def test_browser_route_rejects_antibot_bypass(tmp_path: Path) -> None:
    module = _google_search_contract()
    content = BASE.replace("anti_bot_bypass_allowed: false", "anti_bot_bypass_allowed: true")

    with pytest.raises(ValueError, match="CAPTCHA or anti-bot bypass"):
        module.load_google_search_contract(_write(tmp_path, content))


def test_authorized_browser_status_requires_enabled_route(tmp_path: Path) -> None:
    module = _google_search_contract()
    content = BASE.replace(
        "status: awaiting_eligible_route",
        "status: provider_authorized_browser",
    )

    with pytest.raises(ValueError, match="browser route enabled"):
        module.load_google_search_contract(_write(tmp_path, content))


def test_canonical_replacement_requires_approved_source(tmp_path: Path) -> None:
    module = _google_search_contract()
    content = BASE.replace(
        "status: awaiting_eligible_route",
        "status: canonical_replacement",
    )

    with pytest.raises(ValueError, match="at least one approved source"):
        module.load_google_search_contract(_write(tmp_path, content))


def test_canonical_replacement_can_be_enabled(tmp_path: Path) -> None:
    module = _google_search_contract()
    content = BASE.replace(
        "status: awaiting_eligible_route",
        "status: canonical_replacement",
    ).replace("approved_source_ids: []", "approved_source_ids: [brave-search-api]")
    contract = module.load_google_search_contract(_write(tmp_path, content))

    assert contract.canonical_replacement_source_ids == ("brave-search-api",)
    assert contract.automated_route_available is True


def test_google_api_host_is_exact(tmp_path: Path) -> None:
    module = _google_search_contract()
    content = BASE.replace(
        "https://customsearch.googleapis.com/customsearch/v1",
        "https://customsearch.googleapis.com.evil.example/customsearch/v1",
    )

    with pytest.raises(ValueError, match="official HTTPS API host"):
        module.load_google_search_contract(_write(tmp_path, content))


def test_contract_reference_rejects_non_google_host(tmp_path: Path) -> None:
    module = _google_search_contract()
    content = BASE.replace(
        "https://developers.google.com/custom-search/v1/overview",
        "https://developers.google.com.evil.example/custom-search/v1/overview",
    )

    with pytest.raises(ValueError, match="approved official HTTPS hosts"):
        module.load_google_search_contract(_write(tmp_path, content))

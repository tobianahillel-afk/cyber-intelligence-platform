google_search_contract = __import__(
    "cip.adapters.sources.google_search.contract",
    fromlist=["*"],
)


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
    provider_permission_verified: false
    provider_permission_issued_at: null
    provider_permission_expires_at: null
    human_checkpoint_required: true
    captcha_bypass_allowed: false
    anti_bot_bypass_allowed: false
  canonical_replacement:
    approved_source_ids: []
  analyst_route:
    enabled: true
"""


def _write(tmp_path, content: str):
    path = tmp_path / "google.yml"
    path.write_text(content, encoding="utf-8")
    return path


def _assert_load_value_error(tmp_path, content: str, message: str) -> None:
    try:
        google_search_contract.load_google_search_contract(_write(tmp_path, content))
    except ValueError as exc:
        assert message in str(exc)
    else:
        raise AssertionError(f"expected ValueError containing {message!r}")


def _assert_route_unavailable(contract: object) -> None:
    try:
        contract.require_automated_route()  # type: ignore[attr-defined]
    except google_search_contract.GoogleSearchRouteUnavailable:
        return
    raise AssertionError("expected GoogleSearchRouteUnavailable")


def _existing_api(content: str) -> str:
    return (
        content.replace("status: awaiting_eligible_route", "status: existing_customer_api")
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


def _authorized_browser(
    content: str,
    *,
    issued_at: str = "2026-08-01",
    expires_at: str = "2027-08-01",
) -> str:
    return (
        content.replace("status: awaiting_eligible_route", "status: provider_authorized_browser")
        .replace("enabled: false", "enabled: true", 1)
        .replace(
            "provider_permission_evidence_id: null",
            "provider_permission_evidence_id: google-provider-permission",
        )
        .replace("provider_permission_verified: false", "provider_permission_verified: true")
        .replace(
            "provider_permission_issued_at: null",
            f"provider_permission_issued_at: {issued_at}",
        )
        .replace(
            "provider_permission_expires_at: null",
            f"provider_permission_expires_at: {expires_at}",
        )
    )


def test_default_contract_fails_closed(tmp_path) -> None:
    contract = google_search_contract.load_google_search_contract(_write(tmp_path, BASE))
    assert (
        contract.status
        is google_search_contract.GoogleSearchContractStatus.AWAITING_ELIGIBLE_ROUTE
    )
    assert contract.automated_route_available is False
    assert contract.analyst_route_enabled is True
    _assert_route_unavailable(contract)


def test_existing_customer_api_requires_all_governed_refs(tmp_path) -> None:
    content = BASE.replace(
        "status: awaiting_eligible_route",
        "status: existing_customer_api",
    ).replace(
        "entitlement_evidence_id: null",
        "entitlement_evidence_id: google-existing-customer-approval-2026",
    )
    _assert_load_value_error(tmp_path, content, "API-key refs")


def test_existing_customer_api_can_be_enabled_with_evidence(tmp_path) -> None:
    contract = google_search_contract.load_google_search_contract(
        _write(tmp_path, _existing_api(BASE))
    )
    assert contract.automated_route_available is True
    contract.require_automated_route()


def test_existing_customer_api_rejects_post_sunset_review(tmp_path) -> None:
    content = _existing_api(BASE).replace("reviewed_at: 2026-08-12", "reviewed_at: 2027-01-02")
    _assert_load_value_error(tmp_path, content, "past provider sunset")


def test_browser_route_requires_provider_permission_evidence(tmp_path) -> None:
    content = BASE.replace("enabled: false", "enabled: true", 1)
    _assert_load_value_error(tmp_path, content, "provider permission evidence")


def test_browser_route_rejects_captcha_bypass(tmp_path) -> None:
    content = BASE.replace("captcha_bypass_allowed: false", "captcha_bypass_allowed: true")
    _assert_load_value_error(tmp_path, content, "CAPTCHA or anti-bot bypass")


def test_browser_route_rejects_antibot_bypass(tmp_path) -> None:
    content = BASE.replace("anti_bot_bypass_allowed: false", "anti_bot_bypass_allowed: true")
    _assert_load_value_error(tmp_path, content, "CAPTCHA or anti-bot bypass")


def test_authorized_browser_status_requires_enabled_route(tmp_path) -> None:
    content = BASE.replace(
        "status: awaiting_eligible_route",
        "status: provider_authorized_browser",
    )
    _assert_load_value_error(tmp_path, content, "browser route enabled")


def test_authorized_browser_requires_verified_permission(tmp_path) -> None:
    content = _authorized_browser(BASE).replace(
        "provider_permission_verified: true",
        "provider_permission_verified: false",
    )
    _assert_load_value_error(tmp_path, content, "verified provider permission")


def test_authorized_browser_rejects_future_issuance(tmp_path) -> None:
    content = _authorized_browser(BASE, issued_at="2026-08-13", expires_at="2027-08-13")
    _assert_load_value_error(tmp_path, content, "issuance cannot be after contract review")


def test_authorized_browser_rejects_expired_permission(tmp_path) -> None:
    content = _authorized_browser(BASE, issued_at="2023-11-07", expires_at="2024-11-07")
    _assert_load_value_error(tmp_path, content, "expired at contract review date")


def test_authorized_browser_accepts_current_permission(tmp_path) -> None:
    contract = google_search_contract.load_google_search_contract(
        _write(tmp_path, _authorized_browser(BASE))
    )
    assert contract.automated_route_available is True
    assert contract.browser_permission_verified is True
    assert contract.browser_permission_expires_at is not None


def test_canonical_replacement_requires_approved_source(tmp_path) -> None:
    content = BASE.replace(
        "status: awaiting_eligible_route",
        "status: canonical_replacement",
    )
    _assert_load_value_error(tmp_path, content, "at least one approved source")


def test_canonical_replacement_without_live_proof_fails_closed(tmp_path) -> None:
    content = BASE.replace(
        "status: awaiting_eligible_route",
        "status: canonical_replacement",
    ).replace("approved_source_ids: []", "approved_source_ids: [brave-search-api]")
    contract = google_search_contract.load_google_search_contract(_write(tmp_path, content))
    assert contract.canonical_replacement_source_ids == ("brave-search-api",)
    assert contract.canonical_live_source_ids == ()
    assert contract.automated_route_available is False
    _assert_route_unavailable(contract)


def test_canonical_replacement_requires_approved_live_source(tmp_path) -> None:
    content = BASE.replace(
        "status: awaiting_eligible_route",
        "status: canonical_replacement",
    ).replace("approved_source_ids: []", "approved_source_ids: [brave-search-api]")
    contract = google_search_contract.load_google_search_contract(
        _write(tmp_path, content),
        live_tested_source_ids={"mojeek-search"},
    )
    assert contract.canonical_live_source_ids == ()
    assert contract.automated_route_available is False


def test_canonical_replacement_can_use_approved_live_source(tmp_path) -> None:
    content = BASE.replace(
        "status: awaiting_eligible_route",
        "status: canonical_replacement",
    ).replace("approved_source_ids: []", "approved_source_ids: [brave-search-api]")
    contract = google_search_contract.load_google_search_contract(
        _write(tmp_path, content),
        live_tested_source_ids={"brave-search-api"},
    )
    assert contract.canonical_live_source_ids == ("brave-search-api",)
    assert contract.automated_route_available is True
    contract.require_automated_route()


def test_google_api_host_is_exact(tmp_path) -> None:
    content = BASE.replace(
        "https://customsearch.googleapis.com/customsearch/v1",
        "https://customsearch.googleapis.com.evil.example/customsearch/v1",
    )
    _assert_load_value_error(tmp_path, content, "official HTTPS API host")


def test_contract_reference_rejects_non_google_host(tmp_path) -> None:
    content = BASE.replace(
        "https://developers.google.com/custom-search/v1/overview",
        "https://developers.google.com.evil.example/custom-search/v1/overview",
    )
    _assert_load_value_error(tmp_path, content, "approved official HTTPS hosts")

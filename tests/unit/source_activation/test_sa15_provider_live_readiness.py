def test_mojeek_checked_in_storage_entitlement_remains_fail_closed() -> None:
    with open("policies/mojeek_search_entitlement.yml", encoding="utf-8") as policy_file:
        policy = policy_file.read()

    assert "durable_storage_authorized: false" in policy
    assert "plan: unprovisioned" in policy
    assert "evidence_reference: null" in policy


def test_marginalia_checked_in_entitlement_and_governance_remain_fail_closed() -> None:
    with open(
        "policies/marginalia_search_entitlement.yml", encoding="utf-8"
    ) as entitlement_file:
        entitlement = entitlement_file.read()
    with open(
        "policies/sources.search_providers_sa15.yml", encoding="utf-8"
    ) as governance_file:
        governance = governance_file.read()
    with open(
        "policies/source_activation.search_providers_sa15.yml", encoding="utf-8"
    ) as activation_file:
        activation = activation_file.read()
    with open(
        "policies/source_portfolio.search_providers_sa15.yml", encoding="utf-8"
    ) as portfolio_file:
        portfolio = portfolio_file.read()

    assert "commercial_use_rights: false" in entitlement
    assert "plan: unprovisioned" in entitlement
    assert "evidence_reference: null" in entitlement
    assert "api_key_secret_ref: null" in entitlement

    marginalia_governance = governance.split(
        "  - id: marginalia-web-search-metadata", 1
    )[1]
    assert "status: draft" in marginalia_governance
    assert "status: missing" in marginalia_governance
    assert "approved_hosts: []" in marginalia_governance
    assert "automated_collection_allowed: false" in marginalia_governance

    marginalia_activation = activation.split(
        "  - source_id: marginalia-web-search-metadata", 1
    )[1].split("  - source_id: google-search-governed-route", 1)[0]
    assert "disposition: blocked" in marginalia_activation
    assert "stages: [catalogued, reviewed, mapped, adapter_present]" in marginalia_activation
    assert "live_tested" not in marginalia_activation

    marginalia_portfolio = portfolio.split(
        "  - source_id: marginalia-web-search-metadata", 1
    )[1].split("  - source_id: google-search-governed-route", 1)[0]
    assert "status: candidate" in marginalia_portfolio
    assert "executable: false" in marginalia_portfolio
    assert "runtime_adapter_present: true" in marginalia_portfolio
    assert "adapter_id: marginalia-web-search" in marginalia_portfolio


def test_patentsview_has_no_checked_in_production_target() -> None:
    with open("policies/patentsview_patent_targets.yml", encoding="utf-8") as policy_file:
        policy = policy_file.read()

    assert "targets: []" in policy


def test_search_provider_live_runners_have_valid_controlled_discovery_seed() -> None:
    for script_name in (
        "scripts/live_validate_sa15_brave.py",
        "scripts/live_validate_sa15_mojeek.py",
        "scripts/live_validate_sa15_marginalia.py",
    ):
        with open(script_name, encoding="utf-8") as script_file:
            script = script_file.read()
        assert "seed_urls=(base_url,)" in script
        assert "discover_security_txt=False" in script


def test_marginalia_live_runner_defers_secret_read_to_fail_closed_adapter() -> None:
    with open(
        "scripts/live_validate_sa15_marginalia.py", encoding="utf-8"
    ) as script_file:
        script = script_file.read()

    assert 'token_provider=lambda: _required_env("MARGINALIA_API_KEY")' in script
    assert "MarginaliaSearchAdapter" in script
    assert "load_marginalia_search_entitlement" in script


def test_patentsview_legacy_live_runner_fails_before_reading_any_credential() -> None:
    with open("scripts/live_validate_sa15_patentsview.py", encoding="utf-8") as script_file:
        script = script_file.read()

    assert "PatentsViewCurrentContractUnavailable" in script
    assert "USPTO Open Data Portal" in script
    assert "PATENTSVIEW_API_KEY" not in script
    assert "PatentsViewPatentAdapter" not in script


def test_patentsview_legacy_governance_and_activation_are_revoked() -> None:
    with open("policies/sources.search_archives.yml", encoding="utf-8") as policy_file:
        source_policy = policy_file.read()
    with open(
        "policies/source_activation.search_archives_sa14.yml",
        encoding="utf-8",
    ) as activation_file:
        activation = activation_file.read()

    patentsview_policy = source_policy.split("  - id: patentsview-patent-metadata", 1)[1].split(
        "  - id: w3c-affiliation-specification-metadata", 1
    )[0]
    assert "status: paused" in patentsview_policy
    assert "status: revoked" in patentsview_policy
    assert "approved_hosts: []" in patentsview_policy
    assert "automated_collection_allowed: false" in patentsview_policy

    patentsview_activation = activation.split(
        "  - source_id: patentsview-patent-metadata", 1
    )[1].split("  - source_id: w3c-affiliation-specification-metadata", 1)[0]
    assert "disposition: blocked" in patentsview_activation
    assert "- authorized" not in patentsview_activation
    assert "- executable" not in patentsview_activation
    assert "- live_tested" not in patentsview_activation


def test_manual_live_workflow_exposes_only_prepared_credentialed_provider_runners() -> None:
    with open(
        ".github/workflows/sa15-provider-live-validation.yml", encoding="utf-8"
    ) as workflow_file:
        workflow = workflow_file.read()

    for script_name in (
        "live_validate_sa15_brave.py",
        "live_validate_sa15_mojeek.py",
        "live_validate_sa15_marginalia.py",
    ):
        assert f"python scripts/{script_name}" in workflow
    for secret_name in (
        "BRAVE_SEARCH_API_TOKEN",
        "MOJEEK_API_KEY",
        "MARGINALIA_API_KEY",
    ):
        assert f"secrets.{secret_name}" in workflow
    assert "live_validate_sa15_patentsview.py" not in workflow
    assert "PATENTSVIEW_API_KEY" not in workflow
    assert "live_tested" not in workflow

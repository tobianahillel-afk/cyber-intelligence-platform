def test_mojeek_checked_in_storage_entitlement_remains_fail_closed() -> None:
    with open("policies/mojeek_search_entitlement.yml", encoding="utf-8") as policy_file:
        policy = policy_file.read()

    assert "durable_storage_authorized: false" in policy
    assert "plan: unprovisioned" in policy
    assert "evidence_reference: null" in policy


def test_patentsview_has_no_checked_in_production_target() -> None:
    with open("policies/patentsview_patent_targets.yml", encoding="utf-8") as policy_file:
        policy = policy_file.read()

    assert "targets: []" in policy


def test_manual_live_workflow_references_only_production_runners_and_secret_names() -> None:
    with open(
        ".github/workflows/sa15-provider-live-validation.yml", encoding="utf-8"
    ) as workflow_file:
        workflow = workflow_file.read()

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

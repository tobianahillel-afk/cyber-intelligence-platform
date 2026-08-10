from __future__ import annotations

from pathlib import Path

from cip.modules.collection_orchestration.application.developer_ecosystem_registration import (
    register_developer_ecosystem_adapters,
)
from cip.modules.collection_orchestration.application.ports import CollectionAdapter
from cip.modules.source_governance.infrastructure.registry import load_source_registry

POLICY_PATH = Path("policies/sources.public_web.yml")
EXPECTED_ADAPTERS = {
    ("github-public-org-repositories", "github-org-repositories"),
    ("gitlab-public-group-projects", "gitlab-group-projects"),
    ("pypi-public-package-metadata", "pypi-project-json"),
    ("npm-public-package-metadata", "npm-package-metadata"),
    ("maven-central-public-metadata", "maven-central-search"),
}


def test_all_priority_b2_adapters_are_registered_in_shared_runtime() -> None:
    entries = load_source_registry(POLICY_PATH)
    entries_by_id = {entry.policy.id: entry for entry in entries}
    adapters: dict[tuple[str, str], CollectionAdapter] = {}

    register_developer_ecosystem_adapters(
        adapters,
        entries_by_id,
        (),
        timeout_seconds=20.0,
    )

    assert EXPECTED_ADAPTERS <= set(adapters)

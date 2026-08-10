from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from cip.adapters.sources.developer_ecosystem.registry import (
    DeveloperEcosystemTarget,
    DeveloperTargetKind,
    load_developer_ecosystem_targets,
)
from cip.adapters.sources.developer_ecosystem.schemas import (
    GitHubRepositoryRecord,
    NpmPackageRecord,
    PyPiProjectRecord,
)

ORG_ID = UUID("00000000-0000-0000-0000-000000000820")


def test_checked_in_developer_registry_is_empty() -> None:
    assert load_developer_ecosystem_targets(
        Path("policies/developer_ecosystem_targets.yml")
    ) == ()


@pytest.mark.parametrize(
    ("kind", "namespace", "name"),
    [
        (DeveloperTargetKind.GITHUB_ORG, "example-org", None),
        (DeveloperTargetKind.GITLAB_GROUP, "example-group", None),
        (DeveloperTargetKind.PYPI_PACKAGE, None, "example-package"),
        (DeveloperTargetKind.NPM_PACKAGE, None, "@example/package"),
        (DeveloperTargetKind.MAVEN_ARTIFACT, "com.example", "example-core"),
    ],
)
def test_developer_target_accepts_exact_provider_identity(
    kind: DeveloperTargetKind,
    namespace: str | None,
    name: str | None,
) -> None:
    target = DeveloperEcosystemTarget(
        target_id=f"target-{kind.value}",
        organization_id=ORG_ID,
        kind=kind,
        namespace=namespace,
        name=name,
    )
    assert target.resource_identity


def test_github_schema_drops_owner_and_people_fields() -> None:
    record = GitHubRepositoryRecord.model_validate(
        {
            "id": 1,
            "name": "repo",
            "full_name": "example/repo",
            "html_url": "https://github.com/example/repo",
            "visibility": "public",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-02T00:00:00Z",
            "owner": {"login": "private-person", "email": "private@example.com"},
            "contributors": [{"login": "another-person"}],
        }
    )
    serialized = record.model_dump_json()
    assert "owner" not in serialized
    assert "private-person" not in serialized
    assert "private@example.com" not in serialized
    assert "contributors" not in serialized


def test_pypi_and_npm_schemas_drop_author_and_maintainer_fields() -> None:
    pypi = PyPiProjectRecord.model_validate(
        {
            "info": {
                "name": "example-package",
                "version": "1.2.3",
                "summary": "Example",
                "author": "Private Person",
                "author_email": "private@example.com",
                "maintainer_email": "maintainer@example.com",
            }
        }
    )
    npm = NpmPackageRecord.model_validate(
        {
            "name": "example-package",
            "description": "Example",
            "dist-tags": {"latest": "2.0.0"},
            "maintainers": [{"name": "Private Person", "email": "private@example.com"}],
        }
    )
    combined = pypi.model_dump_json() + npm.model_dump_json(by_alias=True)
    assert "author" not in combined
    assert "maintainer" not in combined
    assert "private@example.com" not in combined

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from cip.adapters.sources.developer_ecosystem.registry import (
    DeveloperEcosystemTarget,
    DeveloperTargetKind,
)
from cip.modules.collection_orchestration.application.maven_central_adapter import (
    MavenCentralArtifactAdapter,
)
from cip.modules.collection_orchestration.application.npm_adapter import NpmPackageAdapter
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.collection_orchestration.application.pypi_adapter import PyPiPackageAdapter
from cip.modules.collection_orchestration.application.repository_metadata_adapters import (
    GitHubOrganizationRepositoriesAdapter,
    GitLabGroupProjectsAdapter,
)
from cip.modules.public_footprint.domain.models import PublicResourceKind
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 10, 11, 30, tzinfo=UTC)
RETENTION = NOW + timedelta(days=365)
JOB_ID = UUID("00000000-0000-0000-0000-000000000830")
ORG_ID = UUID("00000000-0000-0000-0000-000000000831")
POLICY_PATH = Path("policies/sources.public_web.yml")


def test_all_developer_adapters_are_network_idle_without_targets() -> None:
    transport = httpx.MockTransport(_fail_network)
    adapters = (
        GitHubOrganizationRepositoriesAdapter(
            _entry("github-public-org-repositories"), (), transport=transport
        ),
        GitLabGroupProjectsAdapter(
            _entry("gitlab-public-group-projects"), (), transport=transport
        ),
        PyPiPackageAdapter(
            _entry("pypi-public-package-metadata"), (), transport=transport
        ),
        NpmPackageAdapter(
            _entry("npm-public-package-metadata"), (), transport=transport
        ),
        MavenCentralArtifactAdapter(
            _entry("maven-central-public-metadata"), (), transport=transport
        ),
    )
    for adapter in adapters:
        batch = _collect(adapter)
        assert batch.not_modified is True
        assert batch.observations == ()


def test_github_collects_only_public_repository_metadata() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _json([
            _github_record(1, "example/public", "public"),
            _github_record(2, "example/private", "private"),
        ])

    adapter = GitHubOrganizationRepositoriesAdapter(
        _entry("github-public-org-repositories"),
        (_target(DeveloperTargetKind.GITHUB_ORG, namespace="example"),),
        transport=httpx.MockTransport(handler),
    )
    batch = _collect(adapter)

    assert requests[0].url.path == "/orgs/example/repos"
    assert requests[0].url.params["type"] == "public"
    assert requests[0].url.params["per_page"] == "100"
    assert len(batch.observations) == 1
    assert len(batch.public_footprint_projections) == 1
    projection = batch.public_footprint_projections[0]
    assert projection.resource.kind is PublicResourceKind.REPOSITORY
    assert projection.resource.canonical_url == "https://github.com/example/public"
    assert projection.claims == ()


def test_gitlab_collects_public_group_projects_only() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v4/groups/example-group/projects"
        assert request.url.params["visibility"] == "public"
        return _json([
            {
                "id": 10,
                "name": "project",
                "path_with_namespace": "example-group/project",
                "web_url": "https://gitlab.com/example-group/project",
                "visibility": "public",
                "created_at": "2026-01-01T00:00:00Z",
                "last_activity_at": "2026-01-02T00:00:00Z",
                "owner": {"username": "private-person"},
            }
        ])

    adapter = GitLabGroupProjectsAdapter(
        _entry("gitlab-public-group-projects"),
        (_target(DeveloperTargetKind.GITLAB_GROUP, namespace="example-group"),),
        transport=httpx.MockTransport(handler),
    )
    batch = _collect(adapter)
    assert len(batch.public_footprint_projections) == 1
    assert "private-person" not in batch.observations[0].payload_hash_sha256


def test_pypi_maps_exact_package_without_author_metadata() -> None:
    adapter = PyPiPackageAdapter(
        _entry("pypi-public-package-metadata"),
        (_target(DeveloperTargetKind.PYPI_PACKAGE, name="example-package"),),
        transport=httpx.MockTransport(lambda request: _json({
            "info": {
                "name": "example-package",
                "version": "1.2.3",
                "summary": "Example package",
                "author_email": "private@example.com",
            }
        })),
    )
    batch = _collect(adapter)
    projection = batch.public_footprint_projections[0]
    assert projection.resource.kind is PublicResourceKind.PACKAGE
    assert projection.resource.canonical_url == "https://pypi.org/project/example-package/"
    assert projection.claims == ()


def test_npm_maps_exact_package_and_does_not_download_tarball() -> None:
    requested: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request)
        return _json({
            "name": "example-package",
            "description": "Example package",
            "dist-tags": {"latest": "2.0.0"},
            "maintainers": [{"email": "private@example.com"}],
            "versions": {"2.0.0": {"dist": {"tarball": "https://evil.invalid/pkg.tgz"}}},
        })

    adapter = NpmPackageAdapter(
        _entry("npm-public-package-metadata"),
        (_target(DeveloperTargetKind.NPM_PACKAGE, name="example-package"),),
        transport=httpx.MockTransport(handler),
    )
    batch = _collect(adapter)
    assert len(requested) == 1
    assert requested[0].url.host == "registry.npmjs.org"
    assert batch.public_footprint_projections[0].resource.kind is PublicResourceKind.PACKAGE


def test_maven_requires_one_exact_coordinate() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert 'g:"com.example" AND a:"example-core"' in request.url.params["q"]
        return _json({
            "response": {
                "docs": [{
                    "id": "com.example:example-core",
                    "g": "com.example",
                    "a": "example-core",
                    "latestVersion": "3.1.0",
                    "versionCount": 5,
                    "timestamp": 1786302000000,
                    "p": "jar",
                }]
            }
        })

    target = _target(
        DeveloperTargetKind.MAVEN_ARTIFACT,
        namespace="com.example",
        name="example-core",
    )
    adapter = MavenCentralArtifactAdapter(
        _entry("maven-central-public-metadata"),
        (target,),
        transport=httpx.MockTransport(handler),
    )
    batch = _collect(adapter)
    assert batch.public_footprint_projections[0].resource.kind is PublicResourceKind.PACKAGE


def test_pypi_fails_closed_on_wrong_package_identity() -> None:
    adapter = PyPiPackageAdapter(
        _entry("pypi-public-package-metadata"),
        (_target(DeveloperTargetKind.PYPI_PACKAGE, name="expected"),),
        transport=httpx.MockTransport(lambda request: _json({
            "info": {"name": "other", "version": "1.0", "summary": "Other"}
        })),
    )
    with pytest.raises(AdapterExecutionError) as error:
        _collect(adapter)
    assert error.value.error_code == "source_identity_mismatch"


def _collect(adapter):
    return adapter.collect(
        collection_job_id=JOB_ID,
        checkpoint_payload=None,
        collected_at=NOW,
        retention_until=RETENTION,
    )


def _entry(source_id: str) -> SourceRegistryEntry:
    return {entry.policy.id: entry for entry in load_source_registry(POLICY_PATH)}[source_id]


def _target(
    kind: DeveloperTargetKind,
    *,
    namespace: str | None = None,
    name: str | None = None,
) -> DeveloperEcosystemTarget:
    return DeveloperEcosystemTarget(
        target_id=f"target-{kind.value}",
        organization_id=ORG_ID,
        kind=kind,
        namespace=namespace,
        name=name,
        enabled=True,
    )


def _github_record(record_id: int, full_name: str, visibility: str) -> dict[str, object]:
    return {
        "id": record_id,
        "name": full_name.rsplit("/", 1)[-1],
        "full_name": full_name,
        "html_url": f"https://github.com/{full_name}",
        "visibility": visibility,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
    }


def _json(payload: object) -> httpx.Response:
    return httpx.Response(
        200,
        headers={"content-type": "application/json"},
        content=json.dumps(payload).encode("utf-8"),
    )


def _fail_network(_request: httpx.Request) -> httpx.Response:
    raise AssertionError("network must not run")

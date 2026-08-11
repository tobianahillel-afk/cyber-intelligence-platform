from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest

from cip.adapters.sources.developer_ecosystem.registry import (
    DeveloperEcosystemTarget,
    DeveloperTargetKind,
)
from cip.adapters.sources.github_code_search.registry import (
    load_github_code_search_templates,
)
from cip.modules.collection_orchestration.application.github_code_search_adapter import (
    GitHubCodeSearchAdapter,
)
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.public_footprint.domain.search import SearchQueryTemplate
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)
RETENTION = NOW + timedelta(days=90)
ORG_ID = UUID("20a6b15f-5453-5a93-9dd4-ea392e6e8a54")
POLICY_PATH = Path("policies/sources.search_archives.yml")
TEMPLATE_PATH = Path("policies/github_code_search_templates.yml")


def test_checked_in_github_code_search_templates_are_disabled_and_safe() -> None:
    templates = load_github_code_search_templates(TEMPLATE_PATH)
    assert len(templates) == 3
    assert all(template.enabled is False for template in templates)
    assert all("org:{organization}" in template.query_pattern for template in templates)


def test_github_code_search_template_registry_rejects_unsafe_queries(tmp_path: Path) -> None:
    unsafe = tmp_path / "unsafe.yml"
    unsafe.write_text(
        """version: 1
templates:
  - id: unsafe
    version: 1
    query_pattern: "secret org:{organization}"
    purpose: unsafe
    enabled: true
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="may not hunt for secrets"):
        load_github_code_search_templates(unsafe)

    unscoped = tmp_path / "unscoped.yml"
    unscoped.write_text(
        """version: 1
templates:
  - id: unscoped
    version: 1
    query_pattern: "SECURITY.md {organization}"
    purpose: unsafe
    enabled: true
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="must be organization-scoped"):
        load_github_code_search_templates(unscoped)


def test_github_code_search_without_enabled_target_performs_no_network_or_secret_read() -> None:
    secret_reads: list[int] = []

    def token_provider() -> str | None:
        secret_reads.append(1)
        return "token"

    def fail_network(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be used without an enabled target")

    adapter = GitHubCodeSearchAdapter(
        _entry(),
        (_target(enabled=False),),
        (_template(),),
        token_provider=token_provider,
        transport=httpx.MockTransport(fail_network),
    )
    batch = _collect(adapter)
    assert batch.not_modified is True
    assert batch.observations == ()
    assert secret_reads == []


def test_github_code_search_requires_connected_token_before_network() -> None:
    def fail_network(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be used without provider token")

    adapter = GitHubCodeSearchAdapter(
        _entry(),
        (_target(),),
        (_template(),),
        token_provider=lambda: None,
        transport=httpx.MockTransport(fail_network),
    )
    with pytest.raises(AdapterExecutionError) as exc_info:
        _collect(adapter)
    assert exc_info.value.error_code == "provider_not_connected"
    assert exc_info.value.retryable is False


def test_github_code_search_maps_only_public_exact_org_metadata() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "total_count": 4,
                "incomplete_results": False,
                "items": [
                    _item("github/example", "SECURITY.md"),
                    _item("other/example", "SECURITY.md", sha="b" * 40),
                    _item("github/private", "SECURITY.md", private=True, sha="c" * 40),
                    _item(
                        "github/evil",
                        "SECURITY.md",
                        html_url="https://evil.example/github/evil/blob/main/SECURITY.md",
                        sha="d" * 40,
                    ),
                ],
            },
            request=request,
        )

    adapter = GitHubCodeSearchAdapter(
        _entry(),
        (_target(),),
        (_template(),),
        token_provider=lambda: "live-token",
        transport=httpx.MockTransport(handler),
    )
    batch = _collect(adapter)

    assert len(requests) == 1
    request = requests[0]
    assert request.url.path == "/search/code"
    assert request.url.params["q"] == "security org:github filename:SECURITY.md"
    assert request.url.params["per_page"] == "20"
    assert request.url.params["page"] == "1"
    assert request.headers["Authorization"] == "Bearer live-token"
    assert request.headers["X-GitHub-Api-Version"] == "2026-03-10"

    assert len(batch.observations) == 1
    assert len(batch.public_footprint_projections) == 1
    projection = batch.public_footprint_projections[0]
    assert projection.claims == ()
    assert projection.resource.canonical_url.startswith(
        "https://github.com/github/example/blob/"
    )
    assert projection.resource.retrieval_state.value == "quarantined"
    assert "file content not retrieved" in (projection.version.excerpt or "")
    assert batch.checkpoint_payload == {"pair_index": 0}


def test_github_code_search_rejects_invalid_checkpoint() -> None:
    adapter = GitHubCodeSearchAdapter(
        _entry(),
        (_target(),),
        (_template(),),
        token_provider=lambda: "token",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, request=request)),
    )
    with pytest.raises(AdapterExecutionError) as exc_info:
        _collect(adapter, checkpoint_payload={"pair_index": True})
    assert exc_info.value.error_code == "invalid_checkpoint"


def test_github_code_search_classifies_schema_rate_limit_and_incomplete_results() -> None:
    def malformed(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json", request=request)

    malformed_adapter = GitHubCodeSearchAdapter(
        _entry(),
        (_target(),),
        (_template(),),
        token_provider=lambda: "token",
        transport=httpx.MockTransport(malformed),
    )
    with pytest.raises(AdapterExecutionError) as schema_info:
        _collect(malformed_adapter)
    assert schema_info.value.error_code == "source_schema_drift"

    def rate_limited(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, request=request)

    rate_adapter = GitHubCodeSearchAdapter(
        _entry(),
        (_target(),),
        (_template(),),
        token_provider=lambda: "token",
        transport=httpx.MockTransport(rate_limited),
    )
    with pytest.raises(AdapterExecutionError) as rate_info:
        _collect(rate_adapter)
    assert rate_info.value.error_code == "http_429"
    assert rate_info.value.retryable is True

    def incomplete(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"total_count": 1, "incomplete_results": True, "items": []},
            request=request,
        )

    incomplete_adapter = GitHubCodeSearchAdapter(
        _entry(),
        (_target(),),
        (_template(),),
        token_provider=lambda: "token",
        transport=httpx.MockTransport(incomplete),
    )
    with pytest.raises(AdapterExecutionError) as incomplete_info:
        _collect(incomplete_adapter)
    assert incomplete_info.value.error_code == "incomplete_provider_results"
    assert incomplete_info.value.retryable is True


def _entry() -> SourceRegistryEntry:
    return next(
        entry
        for entry in load_source_registry(POLICY_PATH)
        if entry.policy.id == "github-code-search-metadata"
    )


def _target(*, enabled: bool = True) -> DeveloperEcosystemTarget:
    return DeveloperEcosystemTarget(
        target_id="github-code-search-live",
        organization_id=ORG_ID,
        kind=DeveloperTargetKind.GITHUB_ORG,
        namespace="github",
        enabled=enabled,
    )


def _template() -> SearchQueryTemplate:
    return SearchQueryTemplate(
        id="security-policy-metadata",
        version=1,
        query_pattern="security org:{organization} filename:SECURITY.md",
        purpose="public-security-policy-discovery",
        enabled=True,
    )


def _collect(
    adapter: GitHubCodeSearchAdapter,
    *,
    checkpoint_payload: dict[str, object] | None = None,
):
    return adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=checkpoint_payload,
        collected_at=NOW,
        retention_until=RETENTION,
    )


def _item(
    full_name: str,
    path: str,
    *,
    private: bool = False,
    html_url: str | None = None,
    sha: str = "a" * 40,
) -> dict[str, object]:
    repo_name = full_name.split("/", maxsplit=1)[1]
    item_html = html_url or f"https://github.com/{full_name}/blob/{sha}/{path}"
    return {
        "name": path.rsplit("/", maxsplit=1)[-1],
        "path": path,
        "sha": sha,
        "url": f"https://api.github.com/repositories/1/contents/{path}",
        "git_url": f"https://api.github.com/repositories/1/git/blobs/{sha}",
        "html_url": item_html,
        "repository": {
            "id": 1,
            "name": repo_name,
            "full_name": full_name,
            "private": private,
            "html_url": f"https://github.com/{full_name}",
        },
    }

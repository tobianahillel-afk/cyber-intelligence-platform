from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx

from cip.adapters.sources.public_web.client import PublicWebClient
from cip.adapters.sources.public_web.collector import collect_public_web_target
from cip.adapters.sources.public_web.provisioning import (
    AutomaticPublicWebPolicy,
    provision_public_web_target,
)
from cip.modules.organizations.domain.entities import Organization
from cip.modules.public_footprint.domain import DiscoveryMethod

_NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
_ORG_ID = UUID("15712d0d-9054-50b4-8a26-e25d9ea1f509")


def _provisioned(*, max_depth: int = 1, max_pages: int = 5):
    organization = Organization(
        id=_ORG_ID,
        canonical_name="Example Research",
        website_url="https://example.com/",
        created_at=_NOW,
        updated_at=_NOW,
    )
    provisioned = provision_public_web_target(
        organization,
        AutomaticPublicWebPolicy(
            authorization_reference="sa16-l02-test",
            reviewed_at=_NOW,
            max_depth=max_depth,
            max_pages=max_pages,
            max_total_bytes=100_000,
            max_resource_bytes=20_000,
            max_redirects=0,
        ),
        first_crawl_at=_NOW,
    )
    return replace(provisioned.target, discover_security_txt=False), provisioned.source_entry


def _transport(requested: list[str]) -> httpx.MockTransport:
    pages = {
        "https://example.com/": b"""
            <html><head><title>Root</title></head><body>
              <a href="/child">Child</a>
              <a href="https://outside.example/path">Outside</a>
              <a href="/child#duplicate">Duplicate</a>
            </body></html>
        """,
        "https://example.com/child": b"""
            <html><head><title>Child</title></head><body>
              <a href="/grandchild">Grandchild</a>
              <a href="/">Root</a>
            </body></html>
        """,
        "https://example.com/grandchild": b"<html><title>Grandchild</title></html>",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        requested.append(url)
        if url == "https://example.com/robots.txt":
            return httpx.Response(404, request=request)
        body = pages.get(url)
        if body is None:
            raise AssertionError(f"unexpected network request: {url}")
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=body,
            request=request,
        )

    return httpx.MockTransport(handler)


def test_recursive_collection_is_same_origin_bounded_and_depth_aware() -> None:
    target, entry = _provisioned(max_depth=1, max_pages=5)
    requested: list[str] = []

    with httpx.Client(transport=_transport(requested)) as http_client:
        batch = collect_public_web_target(
            PublicWebClient(http_client),
            entry,
            target,
            collection_job_id=uuid4(),
            collected_at=_NOW,
            retention_until=_NOW + timedelta(days=30),
        )

    resource_by_url = {
        projection.resource.canonical_url: projection.resource for projection in batch.projections
    }
    assert set(resource_by_url) == {
        "https://example.com/",
        "https://example.com/child",
    }
    assert resource_by_url["https://example.com/"].discovery_method is DiscoveryMethod.DIRECT
    assert resource_by_url["https://example.com/child"].discovery_method is DiscoveryMethod.LINK
    assert "https://outside.example/path" not in requested
    assert "https://example.com/grandchild" not in requested
    assert requested.count("https://example.com/child") == 1


def test_recursive_collection_rebuilds_frontier_and_replays_checkpoint_safely() -> None:
    target, entry = _provisioned(max_depth=2, max_pages=3)
    first_requested: list[str] = []
    with httpx.Client(transport=_transport(first_requested)) as http_client:
        first = collect_public_web_target(
            PublicWebClient(http_client),
            entry,
            target,
            collection_job_id=uuid4(),
            collected_at=_NOW,
            retention_until=_NOW + timedelta(days=30),
        )

    assert set(first.checkpoint.pages) == {
        "https://example.com/",
        "https://example.com/child",
        "https://example.com/grandchild",
    }

    second_requested: list[str] = []
    with httpx.Client(transport=_transport(second_requested)) as http_client:
        second = collect_public_web_target(
            PublicWebClient(http_client),
            entry,
            target,
            collection_job_id=uuid4(),
            collected_at=_NOW + timedelta(hours=1),
            retention_until=_NOW + timedelta(days=30),
            checkpoint=first.checkpoint,
        )

    assert second.not_modified is True
    assert second.observations == ()
    assert second.checkpoint.pages == first.checkpoint.pages
    assert "https://example.com/grandchild" in second_requested

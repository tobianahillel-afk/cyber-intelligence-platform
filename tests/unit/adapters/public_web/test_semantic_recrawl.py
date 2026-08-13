from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx

from cip.adapters.sources.public_web.checkpoint import dump_checkpoint, load_checkpoint
from cip.adapters.sources.public_web.client import PublicWebClient
from cip.adapters.sources.public_web.collector import collect_public_web_target
from cip.adapters.sources.public_web.provisioning import (
    AutomaticPublicWebPolicy,
    provision_public_web_target,
)
from cip.modules.organizations.domain.entities import Organization

_NOW = datetime(2026, 8, 13, 9, 0, tzinfo=UTC)
_ORG_ID = UUID("66666666-6666-6666-6666-666666666666")
_PAGE_URL = "https://example.com/semantic"
_ETAG = '"semantic-v1"'


def test_legacy_html_checkpoint_is_reprocessed_once_before_etag_recrawl() -> None:
    target, entry = _provisioned()
    validators: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://example.com/robots.txt":
            return httpx.Response(404, request=request)
        if str(request.url) != _PAGE_URL:
            raise AssertionError(f"unexpected network request: {request.url}")
        validator = request.headers.get("if-none-match")
        validators.append(validator)
        if validator == _ETAG:
            return httpx.Response(304, headers={"etag": _ETAG}, request=request)
        return httpx.Response(
            200,
            headers={"content-type": "text/html", "etag": _ETAG},
            content=(
                b'<html><head><script type="application/ld+json">'
                b'{"description":"Kubernetes"}'
                b"</script></head><body>Company page</body></html>"
            ),
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = PublicWebClient(http_client)
        first = collect_public_web_target(
            client,
            entry,
            target,
            collection_job_id=uuid4(),
            collected_at=_NOW,
            retention_until=_NOW + timedelta(days=30),
        )
        assert first.checkpoint.pages[_PAGE_URL].extraction_profile == 2

        legacy_payload = dump_checkpoint(first.checkpoint)
        pages = legacy_payload["pages"]
        assert isinstance(pages, dict)
        state = pages[_PAGE_URL]
        assert isinstance(state, dict)
        del state["extraction_profile"]
        legacy = load_checkpoint(legacy_payload)
        assert legacy is not None
        assert legacy.pages[_PAGE_URL].extraction_profile == 1

        second = collect_public_web_target(
            client,
            entry,
            target,
            collection_job_id=uuid4(),
            collected_at=_NOW + timedelta(hours=1),
            retention_until=_NOW + timedelta(days=30),
            checkpoint=legacy,
        )
        assert second.checkpoint.pages[_PAGE_URL].extraction_profile == 2
        assert second.checkpoint.pages[_PAGE_URL].version_id == first.checkpoint.pages[_PAGE_URL].version_id
        assert any(claim.excerpt == "kubernetes" for claim in second.projections[0].claims)

        third = collect_public_web_target(
            client,
            entry,
            target,
            collection_job_id=uuid4(),
            collected_at=_NOW + timedelta(hours=2),
            retention_until=_NOW + timedelta(days=30),
            checkpoint=second.checkpoint,
        )

    assert validators == [None, None, _ETAG]
    assert third.not_modified is True
    assert third.observations == ()
    assert third.checkpoint.pages[_PAGE_URL].extraction_profile == 2


def _provisioned():
    organization = Organization(
        id=_ORG_ID,
        canonical_name="Example",
        website_url="https://example.com/",
        created_at=_NOW,
        updated_at=_NOW,
    )
    provisioned = provision_public_web_target(
        organization,
        AutomaticPublicWebPolicy(
            authorization_reference="sa16-l05-semantic-recrawl-test",
            reviewed_at=_NOW,
            allowed_path_prefixes=("/",),
            max_link_depth=0,
            discover_sitemaps=False,
            discover_feeds=False,
            max_pages=1,
            max_total_bytes=100_000,
            max_resource_bytes=50_000,
            max_redirects=0,
        ),
        first_crawl_at=_NOW,
    )
    return (
        replace(
            provisioned.target,
            seed_urls=(_PAGE_URL,),
            discover_security_txt=False,
            discover_sitemaps=False,
            discover_feeds=False,
        ),
        provisioned.source_entry,
    )

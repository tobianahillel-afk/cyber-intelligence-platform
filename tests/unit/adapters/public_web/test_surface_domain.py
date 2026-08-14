from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

import pytest

from cip.modules.public_footprint.domain import (
    DiscoveryMethod,
    PublicFootprintProjection,
    PublicResource,
    PublicResourceKind,
    PublicResourceVersion,
    PublicSurfaceKind,
    PublicSurfaceReference,
    ResourceAccessState,
    ResourceRetrievalState,
)


def _projection_parts() -> tuple[PublicResource, PublicResourceVersion]:
    organization_id = uuid4()
    now = datetime(2026, 8, 14, tzinfo=UTC)
    resource = PublicResource(
        organization_id=organization_id,
        source_id="public-web-test",
        source_record_key="https://example.com/",
        canonical_url="https://example.com/",
        source_url="https://example.com/",
        kind=PublicResourceKind.WEB_PAGE,
        discovery_method=DiscoveryMethod.DIRECT,
        first_discovered_at=now,
        last_seen_at=now,
        access_state=ResourceAccessState.PUBLIC,
        retrieval_state=ResourceRetrievalState.FETCHED,
    )
    version = PublicResourceVersion(
        resource_key=resource.identity_key,
        source_url="https://example.com/",
        content_hash_sha256=sha256(b"page").hexdigest(),
        fetched_at=now,
        mime_type="text/html",
        byte_size=4,
    )
    return resource, version


def test_surface_normalizes_fields_and_has_stable_identity() -> None:
    organization_id = uuid4()
    version_id = uuid4()
    first = PublicSurfaceReference(
        organization_id=organization_id,
        resource_version_id=version_id,
        kind=PublicSurfaceKind.FORM_ENDPOINT,
        source_locator=" html:form[action] ",
        target_url="https://EXAMPLE.com:443/search#fragment",
        relation="  Alternate ",
        http_method=" post ",
        media_type=" Text/HTML; charset=UTF-8 ",
    )
    second = PublicSurfaceReference(
        organization_id=organization_id,
        resource_version_id=version_id,
        kind=PublicSurfaceKind.FORM_ENDPOINT,
        source_locator="html:form[action]",
        target_url="https://example.com/search",
        relation="alternate",
        http_method="POST",
        media_type="text/html",
    )

    assert first.target_url == "https://example.com/search"
    assert first.relation == "alternate"
    assert first.http_method == "POST"
    assert first.media_type == "text/html"
    assert first.identity_key == second.identity_key


def test_response_header_requires_name_value_and_no_target() -> None:
    common = {
        "organization_id": uuid4(),
        "resource_version_id": uuid4(),
        "kind": PublicSurfaceKind.RESPONSE_HEADER,
        "source_locator": "header:server",
    }

    with pytest.raises(ValueError, match="require name/value"):
        PublicSurfaceReference(**common)
    with pytest.raises(ValueError, match="require name/value"):
        PublicSurfaceReference(
            **common,
            name="server",
            value="nginx",
            target_url="https://example.com/",
        )

    surface = PublicSurfaceReference(**common, name=" Server ", value=" nginx ")
    assert surface.name == "server"
    assert surface.value == "nginx"


def test_url_surface_requires_target_url() -> None:
    with pytest.raises(ValueError, match="require target_url"):
        PublicSurfaceReference(
            organization_id=uuid4(),
            resource_version_id=uuid4(),
            kind=PublicSurfaceKind.SCRIPT,
            source_locator="html:script[src]",
        )


def test_surface_text_validation_rejects_empty_or_oversized_fields() -> None:
    common = {
        "organization_id": uuid4(),
        "resource_version_id": uuid4(),
        "kind": PublicSurfaceKind.SCRIPT,
        "target_url": "https://example.com/app.js",
    }
    with pytest.raises(ValueError, match="source_locator is required"):
        PublicSurfaceReference(**common, source_locator="   ")
    with pytest.raises(ValueError, match="source_locator cannot exceed"):
        PublicSurfaceReference(**common, source_locator="x" * 501)
    with pytest.raises(ValueError, match="relation cannot exceed"):
        PublicSurfaceReference(
            **common,
            source_locator="html:script[src]",
            relation="x" * 201,
        )
    with pytest.raises(ValueError, match="value cannot exceed"):
        PublicSurfaceReference(
            organization_id=uuid4(),
            resource_version_id=uuid4(),
            kind=PublicSurfaceKind.RESPONSE_HEADER,
            source_locator="header:server",
            name="server",
            value="x" * 2_001,
        )


def test_optional_blank_fields_normalize_to_none() -> None:
    surface = PublicSurfaceReference(
        organization_id=uuid4(),
        resource_version_id=uuid4(),
        kind=PublicSurfaceKind.SCRIPT,
        source_locator="html:script[src]",
        target_url="https://example.com/app.js",
        relation="   ",
        http_method="   ",
        media_type="   ",
    )

    assert surface.relation is None
    assert surface.http_method is None
    assert surface.media_type is None


def test_projection_deduplicates_surfaces() -> None:
    resource, version = _projection_parts()
    surface = PublicSurfaceReference(
        organization_id=resource.organization_id,
        resource_version_id=version.id,
        kind=PublicSurfaceKind.SCRIPT,
        source_locator="html:script[src]",
        target_url="https://example.com/app.js",
    )
    duplicate = PublicSurfaceReference(
        organization_id=resource.organization_id,
        resource_version_id=version.id,
        kind=PublicSurfaceKind.SCRIPT,
        source_locator="html:script[src]",
        target_url="https://example.com/app.js",
    )

    projection = PublicFootprintProjection(
        resource=resource,
        version=version,
        surfaces=(surface, duplicate),
    )

    assert projection.surfaces == (duplicate,)


def test_projection_rejects_surface_from_other_organization_or_version() -> None:
    resource, version = _projection_parts()
    wrong_organization = PublicSurfaceReference(
        organization_id=uuid4(),
        resource_version_id=version.id,
        kind=PublicSurfaceKind.SCRIPT,
        source_locator="html:script[src]",
        target_url="https://example.com/app.js",
    )
    with pytest.raises(ValueError, match="surface organization"):
        PublicFootprintProjection(
            resource=resource,
            version=version,
            surfaces=(wrong_organization,),
        )

    wrong_version = PublicSurfaceReference(
        organization_id=resource.organization_id,
        resource_version_id=uuid4(),
        kind=PublicSurfaceKind.SCRIPT,
        source_locator="html:script[src]",
        target_url="https://example.com/app.js",
    )
    with pytest.raises(ValueError, match="surface version"):
        PublicFootprintProjection(
            resource=resource,
            version=version,
            surfaces=(wrong_version,),
        )

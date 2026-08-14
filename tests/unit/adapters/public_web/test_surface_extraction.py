from uuid import uuid4

from cip.adapters.sources.public_web.client import PublicWebFetchResult
from cip.adapters.sources.public_web.response_headers import (
    bounded_evidence_header_lookup,
    bounded_evidence_headers,
)
from cip.adapters.sources.public_web.surface_extraction import (
    extract_public_surface_references,
)
from cip.modules.public_footprint.domain import PublicSurfaceKind


def _result(body: str, *, mime_type: str = "text/html") -> PublicWebFetchResult:
    return PublicWebFetchResult(
        requested_url="https://example.com/base/index.html",
        fetched_url="https://example.com/base/index.html",
        body=body.encode(),
        mime_type=mime_type,
        etag=None,
        last_modified=None,
        redirects=0,
        response_headers=(
            ("server", "ExampleStack/1.0"),
            ("content-security-policy", "default-src 'self'"),
        ),
    )


def test_extracts_typed_html_surfaces_and_headers() -> None:
    result = _result(
        """
        <html><head>
          <link rel="canonical" href="/canonical">
          <link rel="alternate" hreflang="fr" href="/fr">
          <link rel="alternate" type="application/rss+xml" href="/feed.xml">
          <link rel="stylesheet" href="/assets/site.css">
          <link rel="icon" href="/favicon.ico">
          <script src="/assets/app.js" type="text/javascript"></script>
        </head><body>
          <form action="/search" method="post" enctype="application/x-www-form-urlencoded"></form>
          <a href="/reports/report.pdf">Report</a>
          <img src="/media/logo.png">
          <video src="/media/demo.mp4" poster="/media/poster.jpg"></video>
          <iframe src="/embed/widget"></iframe>
          <object data="/objects/data.bin" type="application/octet-stream"></object>
          <embed src="/embed/plugin.bin" type="application/octet-stream">
        </body></html>
        """
    )

    surfaces = extract_public_surface_references(
        result,
        organization_id=uuid4(),
        resource_version_id=uuid4(),
    )
    kinds = [surface.kind for surface in surfaces]

    assert kinds.count(PublicSurfaceKind.RESPONSE_HEADER) == 2
    assert PublicSurfaceKind.CANONICAL_LINK in kinds
    assert PublicSurfaceKind.ALTERNATE_LINK in kinds
    assert PublicSurfaceKind.STYLESHEET in kinds
    assert PublicSurfaceKind.SCRIPT in kinds
    assert PublicSurfaceKind.RESOURCE_REFERENCE in kinds
    assert PublicSurfaceKind.FORM_ENDPOINT in kinds
    assert PublicSurfaceKind.DOCUMENT_LINK in kinds
    assert PublicSurfaceKind.MEDIA_LINK in kinds
    assert all(
        surface.target_url != "https://example.com/feed.xml" for surface in surfaces
    )

    form = next(
        surface for surface in surfaces if surface.kind is PublicSurfaceKind.FORM_ENDPOINT
    )
    assert form.target_url == "https://example.com/search"
    assert form.http_method == "POST"
    assert form.media_type == "application/x-www-form-urlencoded"

    canonical = next(
        surface for surface in surfaces if surface.kind is PublicSurfaceKind.CANONICAL_LINK
    )
    assert canonical.target_url == "https://example.com/canonical"


def test_deduplicates_and_skips_invalid_url_schemes() -> None:
    result = _result(
        """
        <link rel="canonical" href="/same">
        <link rel="canonical" href="/same">
        <script src="javascript:alert(1)"></script>
        <img src="data:image/png;base64,abc">
        """
    )

    surfaces = extract_public_surface_references(
        result,
        organization_id=uuid4(),
        resource_version_id=uuid4(),
    )

    canonical = [
        surface
        for surface in surfaces
        if surface.kind is PublicSurfaceKind.CANONICAL_LINK
    ]
    assert len(canonical) == 1
    assert not any(surface.kind is PublicSurfaceKind.SCRIPT for surface in surfaces)
    assert not any(surface.kind is PublicSurfaceKind.MEDIA_LINK for surface in surfaces)


def test_caps_surface_inventory() -> None:
    images = "".join(f'<img src="/media/{index}.png">' for index in range(400))
    surfaces = extract_public_surface_references(
        _result(images),
        organization_id=uuid4(),
        resource_version_id=uuid4(),
    )

    assert len(surfaces) == 256
    assert sum(
        surface.kind is PublicSurfaceKind.RESPONSE_HEADER for surface in surfaces
    ) == 2


def test_cap_can_be_reached_inside_multi_surface_tag() -> None:
    images = "".join(f'<img src="/media/{index}.png">' for index in range(253))
    html = images + '<video src="/media/final.mp4" poster="/media/ignored.jpg"></video>'

    surfaces = extract_public_surface_references(
        _result(html),
        organization_id=uuid4(),
        resource_version_id=uuid4(),
    )

    assert len(surfaces) == 256
    assert any(surface.target_url == "https://example.com/media/final.mp4" for surface in surfaces)
    assert all(
        surface.target_url != "https://example.com/media/ignored.jpg" for surface in surfaces
    )


def test_missing_urls_and_document_mime_are_handled_without_network_actions() -> None:
    surfaces = extract_public_surface_references(
        _result(
            """
            <script></script>
            <a>ordinary link without href</a>
            <a type="application/pdf">typed document without href</a>
            <a href="/download" type="application/pdf">typed document</a>
            <script src="/empty-type.js" type=""></script>
            """
        ),
        organization_id=uuid4(),
        resource_version_id=uuid4(),
    )

    assert any(
        surface.kind is PublicSurfaceKind.DOCUMENT_LINK
        and surface.target_url == "https://example.com/download"
        for surface in surfaces
    )
    assert any(
        surface.kind is PublicSurfaceKind.SCRIPT
        and surface.target_url == "https://example.com/empty-type.js"
        and surface.media_type is None
        for surface in surfaces
    )


def test_non_html_only_emits_approved_response_headers() -> None:
    surfaces = extract_public_surface_references(
        _result("not html", mime_type="text/plain"),
        organization_id=uuid4(),
        resource_version_id=uuid4(),
    )

    assert {surface.kind for surface in surfaces} == {PublicSurfaceKind.RESPONSE_HEADER}


def test_header_allowlist_excludes_sensitive_and_normalizes_values() -> None:
    headers = bounded_evidence_headers(
        (
            ("Set-Cookie", "session=secret"),
            ("Authorization", "Bearer secret"),
            ("Server", "  nginx   1.27  "),
            ("X-Powered-By", "Example Framework"),
            ("Content-Language", "   "),
            ("Server", "duplicate ignored"),
        )
    )

    assert headers == (
        ("server", "nginx 1.27"),
        ("x-powered-by", "Example Framework"),
    )


def test_header_values_are_bounded_and_lookup_queries_only_allowlisted_names() -> None:
    queried: list[str] = []

    def header_value(name: str) -> str | None:
        queried.append(name)
        if name == "server":
            return "x" * 3_000
        return None

    headers = bounded_evidence_header_lookup(header_value)

    assert headers == (("server", "x" * 2_000),)
    assert "set-cookie" not in queried
    assert "authorization" not in queried

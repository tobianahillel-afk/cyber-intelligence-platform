from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import BytesIO
from struct import pack
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

import httpx
import pytest
from pypdf import PdfWriter

from cip.adapters.sources.public_web.artifact_context import BrowserArtifactExecutionContext
from cip.adapters.sources.public_web.artifact_download import collect_governed_download
from cip.adapters.sources.public_web.artifact_policy import (
    BrowserArtifactLimits,
    BrowserArtifactPolicyError,
    BrowserArtifactUsage,
)
from cip.adapters.sources.public_web.artifact_screenshot import capture_governed_screenshot
from cip.adapters.sources.public_web.browser_action_authorization import (
    BrowserActionAuthorizationError,
)
from cip.adapters.sources.public_web.client_contract import PublicWebResponseError
from cip.adapters.sources.public_web.ooxml_parsing import DOCX_MIME
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.artifacts import (
    BrowserArtifactKind,
    BrowserScreenshotMode,
)
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionKind,
    BrowserActionPlan,
    BrowserActionStep,
    BrowserHttpMethod,
    BrowserTransitionRule,
)
from cip.modules.public_footprint.domain.models import PublicResourceKind
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    HttpMethod,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

NOW = datetime(2026, 8, 16, 19, 30, tzinfo=UTC)
PAGE_URL = "https://example.com/public/page"


class _Locator:
    def __init__(
        self,
        *,
        present: bool = True,
        kind: str = "div",
        attributes: dict[str, str] | None = None,
        sensitive_descendant: bool = False,
        png: bytes | None = None,
    ) -> None:
        self.present = present
        self.kind = kind
        self.attributes = attributes or {}
        self.sensitive_descendant = sensitive_descendant
        self.png = png or _png(12, 8)

    def count(self) -> int:
        return int(self.present)

    def locator(self, query: str) -> _Locator:
        if query == "xpath=self::a":
            return _Locator(present=self.present and self.kind == "a", kind="a")
        if query == "xpath=self::input":
            return _Locator(present=self.present and self.kind == "input", kind="input")
        if query == "xpath=self::iframe":
            return _Locator(present=self.present and self.kind == "iframe", kind="iframe")
        if ", " in query:
            return _Locator(present=self.sensitive_descendant)
        return _Locator(present=False)

    def get_attribute(self, name: str) -> str | None:
        return self.attributes.get(name)

    def screenshot(self, *, type: str) -> bytes:
        assert type == "png"
        return self.png


class _Page:
    def __init__(self, *, png: bytes | None = None) -> None:
        self.url = PAGE_URL
        self.png = png or _png(20, 10)
        self.root = _Locator()
        self.locators: dict[str, _Locator] = {}

    def locator(self, selector: str) -> _Locator:
        if selector == "html":
            return self.root
        return self.locators.get(selector, _Locator(present=False))

    def screenshot(self, *, type: str, full_page: bool) -> bytes:
        assert type == "png"
        assert full_page is False
        return self.png


def _png(width: int, height: int) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + pack(">II", width, height)


def _target() -> PublicWebTarget:
    return PublicWebTarget(
        id="public-web",
        organization_id=uuid4(),
        canonical_name="Public Web",
        base_url="https://example.com/",
        seed_urls=(PAGE_URL,),
        sitemap_urls=(),
        feed_urls=(),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
        allowed_path_prefixes=("/public",),
        enabled=True,
        authorization_reference="L14-test-approval",
        authorization_reviewed_at=NOW,
        max_pages=10,
        max_total_bytes=20_000_000,
        max_resource_bytes=5_000_000,
        max_redirects=2,
    )


def _entry() -> SourceRegistryEntry:
    return SourceRegistryEntry(
        policy=SourcePolicy(
            id="public-web",
            name="Public Web",
            base_url="https://example.com/",
            status=SourceStatus.ENABLED,
            source_type=SourceType.BROWSER,
            owner="tests",
            licence="controlled L14 fixture",
            allowed_data_categories=frozenset({DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}),
            human_review_required=False,
            raw_content_storage=False,
        ),
        authorization=SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="L14-test-approval",
            reviewed_at=NOW,
            approved_hosts=frozenset({"example.com"}),
            approved_path_prefixes=("/public",),
            approved_purposes=frozenset({"corporate-public-footprint"}),
            approved_http_methods=frozenset({HttpMethod.GET}),
            automated_collection_allowed=True,
            raw_storage_allowed=False,
        ),
        economics={"monthly_cost": 0},
    )


def _plan(step: BrowserActionStep) -> BrowserActionPlan:
    return BrowserActionPlan(
        plan_id=uuid4(),
        version=1,
        source_id="public-web",
        provider_id="fixture",
        target_id="public-web",
        purpose="corporate-public-footprint",
        steps=(step,),
        allowed_transitions=(
            BrowserTransitionRule(
                host="example.com",
                path_prefix="/public",
                methods=frozenset({BrowserHttpMethod.GET}),
            ),
        ),
        max_actions=1,
        max_total_value_chars=0,
    )


def _context(
    client: httpx.Client,
    *,
    limits: BrowserArtifactLimits | None = None,
) -> BrowserArtifactExecutionContext:
    return BrowserArtifactExecutionContext(
        job_id=uuid4(),
        captured_at=NOW,
        retention_until=NOW + timedelta(days=7),
        download_client=client,
        limits=limits or BrowserArtifactLimits(),
    )


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_viewport_screenshot_produces_hash_dimensions_and_provenance() -> None:
    page = _Page(png=_png(640, 480))
    step = BrowserActionStep(
        "shot",
        BrowserActionKind.SCREENSHOT,
        screenshot_mode=BrowserScreenshotMode.VIEWPORT,
    )
    client = _client(lambda _request: httpx.Response(500))
    context = _context(client)
    try:
        artifact = capture_governed_screenshot(
            page, _target(), _entry(), _plan(step), step, context, BrowserArtifactUsage()
        )
    finally:
        client.close()

    assert artifact.kind is BrowserArtifactKind.SCREENSHOT
    assert artifact.viewport_width == 640
    assert artifact.viewport_height == 480
    assert artifact.raw_retained is False
    assert artifact.source_locator.endswith(":shot")


def test_screenshot_denies_sensitive_descendant_and_sensitive_root() -> None:
    page = _Page()
    page.root = _Locator(sensitive_descendant=True)
    step = BrowserActionStep(
        "shot",
        BrowserActionKind.SCREENSHOT,
        screenshot_mode=BrowserScreenshotMode.VIEWPORT,
    )
    client = _client(lambda _request: httpx.Response(500))
    context = _context(client)
    try:
        with pytest.raises(BrowserArtifactPolicyError, match="sensitive_surface_denied"):
            capture_governed_screenshot(
                page, _target(), _entry(), _plan(step), step, context, BrowserArtifactUsage()
            )

        page.root = _Locator()
        page.locators["#secret"] = _Locator(
            kind="input",
            attributes={"type": "password"},
        )
        element = BrowserActionStep(
            "element",
            BrowserActionKind.SCREENSHOT,
            selector="#secret",
            screenshot_mode=BrowserScreenshotMode.ELEMENT,
        )
        with pytest.raises(BrowserArtifactPolicyError, match="sensitive_surface_denied"):
            capture_governed_screenshot(
                page,
                _target(),
                _entry(),
                _plan(element),
                element,
                context,
                BrowserArtifactUsage(),
            )
    finally:
        client.close()


def test_text_download_is_quarantined_parsed_and_projected() -> None:
    url = "https://example.com/public/report.txt"
    page = _Page()
    page.locators["a#report"] = _Locator(kind="a", attributes={"href": url})
    step = BrowserActionStep(
        "download",
        BrowserActionKind.DOWNLOAD,
        selector="a#report",
        expected_download_url=url,
    )
    client = _client(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "text/plain"},
            content=b"Quarterly public report",
            request=request,
        )
    )
    context = _context(client)
    try:
        artifact, projection = collect_governed_download(
            page,
            _target(),
            _entry(),
            _plan(step),
            step,
            context,
            BrowserArtifactUsage(),
            timeout_ms=5_000,
        )
    finally:
        client.close()

    assert artifact.kind is BrowserArtifactKind.DOWNLOAD
    assert artifact.media_type == "text/plain"
    assert artifact.excerpt == "Quarterly public report"
    assert projection.resource.kind is PublicResourceKind.DOCUMENT
    assert projection.version.excerpt == "Quarterly public report"


def test_download_denies_off_origin_link_before_network() -> None:
    url = "https://evil.example/public/report.txt"
    page = _Page()
    page.locators["a#report"] = _Locator(kind="a", attributes={"href": url})
    step = BrowserActionStep(
        "download",
        BrowserActionKind.DOWNLOAD,
        selector="a#report",
        expected_download_url=url,
    )
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, content=b"never", request=request)

    client = _client(handler)
    context = _context(client)
    try:
        with pytest.raises(BrowserActionAuthorizationError, match="off_origin"):
            collect_governed_download(
                page,
                _target(),
                _entry(),
                _plan(step),
                step,
                context,
                BrowserArtifactUsage(),
                timeout_ms=5_000,
            )
    finally:
        client.close()
    assert calls == 0


def test_download_redirect_is_reauthorized_and_off_origin_denied() -> None:
    url = "https://example.com/public/report.txt"
    page = _Page()
    page.locators["a#report"] = _Locator(kind="a", attributes={"href": url})
    step = BrowserActionStep(
        "download",
        BrowserActionKind.DOWNLOAD,
        selector="a#report",
        expected_download_url=url,
    )
    client = _client(
        lambda request: httpx.Response(
            302,
            headers={"location": "https://evil.example/public/report.txt"},
            request=request,
        )
    )
    context = _context(client)
    try:
        with pytest.raises(BrowserActionAuthorizationError, match="off_origin"):
            collect_governed_download(
                page,
                _target(),
                _entry(),
                _plan(step),
                step,
                context,
                BrowserArtifactUsage(),
                timeout_ms=5_000,
            )
    finally:
        client.close()


def test_oversized_download_is_denied_by_streaming_transport() -> None:
    url = "https://example.com/public/report.txt"
    page = _Page()
    page.locators["a#report"] = _Locator(kind="a", attributes={"href": url})
    step = BrowserActionStep(
        "download",
        BrowserActionKind.DOWNLOAD,
        selector="a#report",
        expected_download_url=url,
    )
    limits = BrowserArtifactLimits(max_artifact_bytes=4, max_total_download_bytes=4)
    client = _client(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "text/plain", "content-length": "5"},
            content=b"12345",
            request=request,
        )
    )
    context = _context(client, limits=limits)
    try:
        with pytest.raises(PublicWebResponseError, match="size limit"):
            collect_governed_download(
                page,
                _target(),
                _entry(),
                _plan(step),
                step,
                context,
                BrowserArtifactUsage(),
                timeout_ms=5_000,
            )
    finally:
        client.close()


def test_download_count_budget_blocks_second_attempt() -> None:
    url = "https://example.com/public/report.txt"
    page = _Page()
    page.locators["a#report"] = _Locator(kind="a", attributes={"href": url})
    step = BrowserActionStep(
        "download",
        BrowserActionKind.DOWNLOAD,
        selector="a#report",
        expected_download_url=url,
    )
    client = _client(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "text/plain"},
            content=b"ok",
            request=request,
        )
    )
    context = _context(client, limits=BrowserArtifactLimits(max_downloads=1))
    usage = BrowserArtifactUsage()
    try:
        collect_governed_download(
            page, _target(), _entry(), _plan(step), step, context, usage, timeout_ms=5_000
        )
        with pytest.raises(BrowserArtifactPolicyError, match="count_budget"):
            collect_governed_download(
                page, _target(), _entry(), _plan(step), step, context, usage, timeout_ms=5_000
            )
    finally:
        client.close()


def test_pdf_download_reuses_existing_pdf_parser() -> None:
    url = "https://example.com/public/report.pdf"
    pdf = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(pdf)
    artifact, projection = _collect_document(url, "application/pdf", pdf.getvalue())

    assert artifact.media_type == "application/pdf"
    assert projection.version.mime_type == "application/pdf"


def test_docx_download_reuses_existing_ooxml_parser() -> None:
    url = "https://example.com/public/report.docx"
    body = _minimal_docx("Controlled public evidence")
    artifact, projection = _collect_document(url, DOCX_MIME, body)

    assert artifact.media_type == DOCX_MIME
    assert projection.version.excerpt == "Controlled public evidence"


def _collect_document(
    url: str,
    media_type: str,
    body: bytes,
):
    page = _Page()
    page.locators["a#report"] = _Locator(kind="a", attributes={"href": url})
    step = BrowserActionStep(
        "download",
        BrowserActionKind.DOWNLOAD,
        selector="a#report",
        expected_download_url=url,
    )
    client = _client(
        lambda request: httpx.Response(
            200,
            headers={"content-type": media_type},
            content=body,
            request=request,
        )
    )
    context = _context(client)
    try:
        return collect_governed_download(
            page,
            _target(),
            _entry(),
            _plan(step),
            step,
            context,
            BrowserArtifactUsage(),
            timeout_ms=5_000,
        )
    finally:
        client.close()


def _minimal_docx(text: str) -> bytes:
    buffer = BytesIO()
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Override PartName="/word/document.xml" '
        f'ContentType="{DOCX_MIME}.main+xml"/>'
        "</Types>"
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    )
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()

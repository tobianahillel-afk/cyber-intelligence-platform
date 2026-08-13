from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from cip.adapters.sources.public_web.client import PublicWebFetchResult
from cip.adapters.sources.public_web.content_extraction import extract_public_content
from cip.adapters.sources.public_web.document_parsing import PublicDocumentParseError
from cip.adapters.sources.public_web.ooxml_parsing import (
    DOCX_MIME,
    PPTX_MIME,
    XLSX_MIME,
    extract_ooxml_text,
)
from cip.modules.public_footprint.domain.scope import CrawlScope


def test_extracts_docx_text_and_core_title() -> None:
    body = _package(
        main_part="word/document.xml",
        main_content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
        ),
        parts={
            "word/document.xml": _word_xml("Zero Trust", "Kubernetes"),
            "docProps/core.xml": _core_xml("Security architecture"),
        },
    )

    extracted = extract_ooxml_text(body, mime_type=DOCX_MIME)

    assert extracted.title == "Security architecture"
    assert extracted.text == "Zero Trust Kubernetes"


def test_extracts_xlsx_shared_inline_and_string_cells() -> None:
    body = _package(
        main_part="xl/workbook.xml",
        main_content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
        ),
        parts={
            "xl/workbook.xml": "<workbook/>",
            "xl/sharedStrings.xml": (
                '<sst xmlns="urn:x"><si><t>Kubernetes</t></si><si><t>Azure</t></si></sst>'
            ),
            "xl/worksheets/sheet1.xml": (
                '<worksheet xmlns="urn:x"><sheetData><row>'
                '<c t="s"><v>0</v></c>'
                '<c t="inlineStr"><is><t>Zero Trust</t></is></c>'
                '<c t="str"><v>Splunk</v></c>'
                '<c><v>123</v></c>'
                "</row></sheetData></worksheet>"
            ),
        },
    )

    extracted = extract_ooxml_text(body, mime_type=XLSX_MIME)

    assert extracted.text == "Kubernetes Zero Trust Splunk"


def test_extracts_pptx_slide_text_without_following_relationships() -> None:
    body = _package(
        main_part="ppt/presentation.xml",
        main_content_type=(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"
        ),
        parts={
            "ppt/presentation.xml": "<p:presentation xmlns:p=\"urn:p\"/>",
            "ppt/slides/slide1.xml": _slide_xml("CrowdStrike"),
            "ppt/slides/slide2.xml": _slide_xml("Incident Response"),
            "ppt/slides/_rels/slide1.xml.rels": (
                '<Relationships xmlns="urn:r"><Relationship TargetMode="External" '
                'Target="https://outside.example/"/></Relationships>'
            ),
        },
    )

    extracted = extract_ooxml_text(body, mime_type=PPTX_MIME)

    assert extracted.text == "CrowdStrike Incident Response"
    assert "outside.example" not in extracted.text


def test_rejects_mime_package_mismatch() -> None:
    body = _package(
        main_part="word/document.xml",
        main_content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
        ),
        parts={"word/document.xml": _word_xml("Kubernetes")},
    )

    with pytest.raises(PublicDocumentParseError):
        extract_ooxml_text(body, mime_type=PPTX_MIME)


def test_rejects_macro_bearing_package() -> None:
    body = _package(
        main_part="word/document.xml",
        main_content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
        ),
        parts={
            "word/document.xml": _word_xml("Kubernetes"),
            "word/vbaProject.bin": b"macro",
        },
    )

    with pytest.raises(PublicDocumentParseError, match="macro-bearing"):
        extract_ooxml_text(body, mime_type=DOCX_MIME)


def test_rejects_dtd_or_entity_declarations() -> None:
    body = _package(
        main_part="word/document.xml",
        main_content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
        ),
        parts={
            "word/document.xml": (
                '<!DOCTYPE x [<!ENTITY leak SYSTEM "file:///etc/passwd">]>'
                '<w:document xmlns:w="urn:w"><w:t>&leak;</w:t></w:document>'
            )
        },
    )

    with pytest.raises(PublicDocumentParseError, match="declarations"):
        extract_ooxml_text(body, mime_type=DOCX_MIME)


def test_rejects_unsafe_zip_entry_path() -> None:
    body = _package(
        main_part="word/document.xml",
        main_content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
        ),
        parts={
            "word/document.xml": _word_xml("Kubernetes"),
            "../escape.xml": "<x/>",
        },
    )

    with pytest.raises(PublicDocumentParseError, match="unsafe entry path"):
        extract_ooxml_text(body, mime_type=DOCX_MIME)


def test_public_content_routes_docx_through_document_projection() -> None:
    body = _package(
        main_part="word/document.xml",
        main_content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
        ),
        parts={
            "word/document.xml": _word_xml("Kubernetes architecture"),
            "docProps/core.xml": _core_xml("Architecture note"),
        },
    )
    result = PublicWebFetchResult(
        requested_url="https://example.com/security.docx",
        fetched_url="https://example.com/security.docx",
        body=body,
        mime_type=DOCX_MIME,
        etag=None,
        last_modified=None,
        redirects=0,
    )

    extracted = extract_public_content(result, quarantined=False, tombstoned=False)

    assert extracted is not None
    assert extracted.title == "Architecture note"
    assert extracted.text == "Kubernetes architecture"
    assert extracted.excerpt == "Kubernetes architecture"


def test_default_crawl_scope_allows_ooxml_mime_types() -> None:
    scope = CrawlScope(allowed_hosts=frozenset({"example.com"}))

    assert DOCX_MIME in scope.allowed_mime_types
    assert XLSX_MIME in scope.allowed_mime_types
    assert PPTX_MIME in scope.allowed_mime_types


def _package(
    *,
    main_part: str,
    main_content_type: str,
    parts: dict[str, str | bytes],
) -> bytes:
    buffer = BytesIO()
    content_types = (
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        f'<Override PartName="/{main_part}" ContentType="{main_content_type}"/>'
        "</Types>"
    )
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        for name, value in parts.items():
            archive.writestr(name, value)
    return buffer.getvalue()


def _word_xml(*values: str) -> str:
    text = "".join(f"<w:r><w:t>{value}</w:t></w:r>" for value in values)
    return f'<w:document xmlns:w="urn:w"><w:body><w:p>{text}</w:p></w:body></w:document>'


def _slide_xml(value: str) -> str:
    return (
        '<p:sld xmlns:p="urn:p" xmlns:a="urn:a"><p:cSld><a:p><a:r>'
        f"<a:t>{value}</a:t>"
        "</a:r></a:p></p:cSld></p:sld>"
    )


def _core_xml(title: str) -> str:
    return (
        '<cp:coreProperties xmlns:cp="urn:cp" xmlns:dc="urn:dc">'
        f"<dc:title>{title}</dc:title>"
        "</cp:coreProperties>"
    )

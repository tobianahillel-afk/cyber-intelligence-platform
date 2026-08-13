from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

import pytest

from cip.adapters.sources.public_web.document_parsing import PublicDocumentParseError
from cip.adapters.sources.public_web.ooxml_parsing import (
    DOCX_MIME,
    PPTX_MIME,
    XLSX_MIME,
    detect_ooxml_mime,
    extract_ooxml_text,
)

_DOCX_MAIN_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
)
_XLSX_MAIN_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
)
_PPTX_MAIN_TYPE = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"
)


def test_rejects_unsupported_mime_empty_oversize_and_non_zip_payloads() -> None:
    with pytest.raises(PublicDocumentParseError, match="unsupported"):
        extract_ooxml_text(b"PK", mime_type="application/zip")
    with pytest.raises(PublicDocumentParseError, match="byte limit"):
        extract_ooxml_text(b"", mime_type=DOCX_MIME)
    with pytest.raises(PublicDocumentParseError, match="byte limit"):
        extract_ooxml_text(b"PK" + b"x" * 5_000_000, mime_type=DOCX_MIME)
    with pytest.raises(PublicDocumentParseError, match="not a ZIP"):
        extract_ooxml_text(b"not-a-package", mime_type=DOCX_MIME)


def test_malformed_zip_is_wrapped_as_safe_parse_error() -> None:
    with pytest.raises(PublicDocumentParseError, match="parsed safely"):
        extract_ooxml_text(b"PKbroken", mime_type=DOCX_MIME)


def test_rejects_duplicate_zip_entries() -> None:
    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_STORED) as archive:
        content_types = _content_types("word/document.xml", _DOCX_MAIN_TYPE)
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("word/document.xml", _word_xml("first"))
        archive.writestr("word/document.xml", _word_xml("second"))

    with pytest.raises(PublicDocumentParseError, match="duplicate entries"):
        extract_ooxml_text(buffer.getvalue(), mime_type=DOCX_MIME)


def test_rejects_missing_required_main_or_content_type_parts() -> None:
    only_types = _zip_parts(
        {"[Content_Types].xml": _content_types("word/document.xml", _DOCX_MAIN_TYPE)}
    )
    only_main = _zip_parts({"word/document.xml": _word_xml("text")})

    with pytest.raises(PublicDocumentParseError, match="does not match"):
        extract_ooxml_text(only_types, mime_type=DOCX_MIME)
    with pytest.raises(PublicDocumentParseError, match="does not match"):
        extract_ooxml_text(only_main, mime_type=DOCX_MIME)


def test_missing_or_blank_core_title_is_not_fabricated() -> None:
    no_core = _docx({"word/document.xml": _word_xml("Kubernetes")})
    blank_core_xml = (
        '<cp:coreProperties xmlns:cp="urn:cp" xmlns:dc="urn:dc">'
        "<dc:title>   </dc:title>"
        "</cp:coreProperties>"
    )
    blank_core = _docx(
        {
            "word/document.xml": _word_xml("Kubernetes"),
            "docProps/core.xml": blank_core_xml,
        }
    )

    assert extract_ooxml_text(no_core, mime_type=DOCX_MIME).title is None
    assert extract_ooxml_text(blank_core, mime_type=DOCX_MIME).title is None


def test_xlsx_without_shared_strings_ignores_invalid_shared_indices() -> None:
    body = _xlsx(
        {
            "xl/workbook.xml": "<workbook/>",
            "xl/worksheets/sheet1.xml": (
                '<worksheet xmlns="urn:x"><sheetData><row>'
                '<c t="s"><v>9</v></c>'
                '<c t="s"><v>not-an-index</v></c>'
                '<c t="str"><v>  Zero   Trust  </v></c>'
                '<c t="inlineStr"><is><t> Kubernetes </t></is></c>'
                '<c t="str"></c>'
                "</row></sheetData></worksheet>"
            ),
        }
    )

    extracted = extract_ooxml_text(body, mime_type=XLSX_MIME)

    assert extracted.text == "Zero Trust Kubernetes"


def test_detector_rejects_malformed_and_incomplete_packages() -> None:
    incomplete = _zip_parts({"word/document.xml": _word_xml("Kubernetes")})

    assert detect_ooxml_mime(b"", url_path="/report.docx") is None
    assert detect_ooxml_mime(b"PKbroken", url_path="/report.docx") is None
    assert detect_ooxml_mime(incomplete, url_path="/report.docx") is None


def test_rejects_high_compression_ratio_package() -> None:
    body = _docx(
        {
            "word/document.xml": _word_xml("A" * 50_000),
        }
    )

    with pytest.raises(PublicDocumentParseError, match="compression-ratio"):
        extract_ooxml_text(body, mime_type=DOCX_MIME)


def test_rejects_malformed_required_xml() -> None:
    body = _docx({"word/document.xml": "<w:document>"})

    with pytest.raises(PublicDocumentParseError, match="malformed"):
        extract_ooxml_text(body, mime_type=DOCX_MIME)


def test_rejects_utf16_doctype_and_entity_declarations() -> None:
    document = (
        '<?xml version="1.0" encoding="UTF-16"?>'
        '<!DOCTYPE w:document [<!ENTITY payload "expanded">]>'
        '<w:document xmlns:w="urn:w"><w:body><w:p><w:r>'
        "<w:t>&payload;</w:t>"
        "</w:r></w:p></w:body></w:document>"
    ).encode("utf-16")
    body = _docx({"word/document.xml": document})

    with pytest.raises(PublicDocumentParseError, match="declarations"):
        extract_ooxml_text(body, mime_type=DOCX_MIME)


def test_rejects_malformed_xlsx_and_pptx_main_parts() -> None:
    xlsx = _xlsx(
        {
            "xl/workbook.xml": "<workbook>",
            "xl/worksheets/sheet1.xml": '<worksheet xmlns="urn:x"/>',
        }
    )
    pptx = _pptx(
        {
            "ppt/presentation.xml": "<p:presentation>",
            "ppt/slides/slide1.xml": (
                '<p:sld xmlns:p="urn:p" xmlns:a="urn:a">'
                "<a:p><a:r><a:t>text</a:t></a:r></a:p>"
                "</p:sld>"
            ),
        }
    )

    with pytest.raises(PublicDocumentParseError, match="malformed"):
        extract_ooxml_text(xlsx, mime_type=XLSX_MIME)
    with pytest.raises(PublicDocumentParseError, match="malformed"):
        extract_ooxml_text(pptx, mime_type=PPTX_MIME)


def test_preserves_adjacent_runs_and_structural_boundaries() -> None:
    docx = _docx(
        {
            "word/document.xml": (
                '<w:document xmlns:w="urn:w"><w:body>'
                "<w:p><w:r><w:t>Cyber</w:t></w:r>"
                "<w:r><w:t>security</w:t></w:r></w:p>"
                "<w:p><w:r><w:t>platform</w:t></w:r></w:p>"
                "</w:body></w:document>"
            )
        }
    )
    xlsx = _xlsx(
        {
            "xl/workbook.xml": "<workbook/>",
            "xl/sharedStrings.xml": (
                '<sst xmlns="urn:x"><si>'
                "<r><t>Cyber</t></r><r><t>security</t></r>"
                "</si></sst>"
            ),
            "xl/worksheets/sheet1.xml": (
                '<worksheet xmlns="urn:x"><sheetData><row>'
                '<c t="s"><v>0</v></c>'
                '<c t="inlineStr"><is><r><t>Zero</t></r>'
                "<r><t>Trust</t></r></is></c>"
                "</row></sheetData></worksheet>"
            ),
        }
    )
    pptx = _pptx(
        {
            "ppt/presentation.xml": '<p:presentation xmlns:p="urn:p"/>',
            "ppt/slides/slide1.xml": (
                '<p:sld xmlns:p="urn:p" xmlns:a="urn:a">'
                "<a:p><a:r><a:t>Cyber</a:t></a:r>"
                "<a:r><a:t>security</a:t></a:r></a:p>"
                "<a:p><a:r><a:t>platform</a:t></a:r></a:p>"
                "</p:sld>"
            ),
        }
    )

    assert extract_ooxml_text(docx, mime_type=DOCX_MIME).text == "Cybersecurity platform"
    assert extract_ooxml_text(xlsx, mime_type=XLSX_MIME).text == "Cybersecurity ZeroTrust"
    assert extract_ooxml_text(pptx, mime_type=PPTX_MIME).text == "Cybersecurity platform"


def _docx(parts: dict[str, str | bytes]) -> bytes:
    merged = {
        "[Content_Types].xml": _content_types("word/document.xml", _DOCX_MAIN_TYPE),
        **parts,
    }
    return _zip_parts(merged)


def _xlsx(parts: dict[str, str | bytes]) -> bytes:
    merged = {
        "[Content_Types].xml": _content_types("xl/workbook.xml", _XLSX_MAIN_TYPE),
        **parts,
    }
    return _zip_parts(merged)


def _pptx(parts: dict[str, str | bytes]) -> bytes:
    merged = {
        "[Content_Types].xml": _content_types(
            "ppt/presentation.xml",
            _PPTX_MAIN_TYPE,
        ),
        **parts,
    }
    return _zip_parts(merged)


def _zip_parts(parts: dict[str, str | bytes]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        for name, value in parts.items():
            archive.writestr(name, value)
    return buffer.getvalue()


def _content_types(main_part: str, main_type: str) -> str:
    return (
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        f'<Override PartName="/{main_part}" ContentType="{main_type}"/>'
        "</Types>"
    )


def _word_xml(value: str) -> str:
    return (
        '<w:document xmlns:w="urn:w"><w:body><w:p><w:r><w:t>'
        f"{value}"
        "</w:t></w:r></w:p></w:body></w:document>"
    )

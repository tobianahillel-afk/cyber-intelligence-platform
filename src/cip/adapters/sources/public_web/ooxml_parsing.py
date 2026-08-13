from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath
from xml.etree import ElementTree
from zipfile import BadZipFile, LargeZipFile, ZipFile, ZipInfo

from cip.adapters.sources.public_web.document_parsing import (
    ExtractedDocument,
    PublicDocumentParseError,
)

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

_MAX_PACKAGE_BYTES = 5_000_000
_MAX_ENTRIES = 256
_MAX_TOTAL_UNCOMPRESSED_BYTES = 20_000_000
_MAX_ENTRY_BYTES = 2_000_000
_MAX_COMPRESSION_RATIO = 100
_MAX_EXTRACTED_CHARS = 100_000
_MAX_TITLE_CHARS = 1_000


@dataclass(frozen=True, slots=True)
class _PackageSpec:
    mime_type: str
    main_part: str
    main_content_type: str


_SPECS = {
    DOCX_MIME: _PackageSpec(
        mime_type=DOCX_MIME,
        main_part="word/document.xml",
        main_content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
        ),
    ),
    XLSX_MIME: _PackageSpec(
        mime_type=XLSX_MIME,
        main_part="xl/workbook.xml",
        main_content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
        ),
    ),
    PPTX_MIME: _PackageSpec(
        mime_type=PPTX_MIME,
        main_part="ppt/presentation.xml",
        main_content_type=(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"
        ),
    ),
}


def extract_ooxml_text(body: bytes, *, mime_type: str) -> ExtractedDocument:
    spec = _SPECS.get(mime_type.casefold())
    if spec is None:
        raise PublicDocumentParseError("unsupported Office Open XML MIME type")
    if not body or len(body) > _MAX_PACKAGE_BYTES:
        raise PublicDocumentParseError("Office Open XML package exceeds the parser byte limit")
    if not body.startswith(b"PK"):
        raise PublicDocumentParseError("Office Open XML response is not a ZIP package")
    try:
        with ZipFile(BytesIO(body), mode="r", allowZip64=False) as archive:
            entries = _validate_archive(archive)
            _validate_content_types(archive, entries, spec)
            title = _core_title(archive, entries)
            text = _extract_package_text(archive, entries, spec)
    except PublicDocumentParseError:
        raise
    except (BadZipFile, LargeZipFile, OSError, RuntimeError) as exc:
        raise PublicDocumentParseError(
            "Office Open XML package could not be parsed safely"
        ) from exc
    return ExtractedDocument(title=title, language=None, text=text)


def _validate_archive(archive: ZipFile) -> dict[str, ZipInfo]:
    infos = archive.infolist()
    if not infos or len(infos) > _MAX_ENTRIES:
        raise PublicDocumentParseError("Office Open XML package has an invalid entry count")
    total_uncompressed = 0
    entries: dict[str, ZipInfo] = {}
    for info in infos:
        name = _validate_entry_name(info.filename)
        if name in entries:
            raise PublicDocumentParseError("Office Open XML package contains duplicate entries")
        if info.flag_bits & 0x1:
            raise PublicDocumentParseError("encrypted Office Open XML entries are not processed")
        if name.casefold().endswith("vbaproject.bin"):
            raise PublicDocumentParseError(
                "macro-bearing Office Open XML packages are not processed"
            )
        if info.file_size < 0 or info.file_size > _MAX_ENTRY_BYTES:
            raise PublicDocumentParseError("Office Open XML entry exceeds the parser byte limit")
        total_uncompressed += info.file_size
        if total_uncompressed > _MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise PublicDocumentParseError("Office Open XML package exceeds the expansion limit")
        if _compression_ratio(info) > _MAX_COMPRESSION_RATIO:
            raise PublicDocumentParseError(
                "Office Open XML entry exceeds the compression-ratio limit"
            )
        entries[name] = info
    return entries


def _validate_entry_name(value: str) -> str:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts or normalized.startswith("/"):
        raise PublicDocumentParseError("Office Open XML package contains an unsafe entry path")
    return normalized


def _compression_ratio(info: ZipInfo) -> int:
    if info.file_size == 0:
        return 0
    if info.compress_size <= 0:
        return _MAX_COMPRESSION_RATIO + 1
    return (info.file_size + info.compress_size - 1) // info.compress_size


def _validate_content_types(
    archive: ZipFile,
    entries: dict[str, ZipInfo],
    spec: _PackageSpec,
) -> None:
    if "[Content_Types].xml" not in entries or spec.main_part not in entries:
        raise PublicDocumentParseError("Office Open XML package is missing required parts")
    root = _read_xml(archive, entries["[Content_Types].xml"])
    expected_part = f"/{spec.main_part}"
    for node in root.iter():
        if _local_name(node.tag) != "Override":
            continue
        if node.attrib.get("PartName") != expected_part:
            continue
        actual = node.attrib.get("ContentType", "").casefold()
        if actual == spec.main_content_type.casefold():
            return
    raise PublicDocumentParseError("Office Open XML package type does not match the response MIME")


def _core_title(archive: ZipFile, entries: dict[str, ZipInfo]) -> str | None:
    info = entries.get("docProps/core.xml")
    if info is None:
        return None
    root = _read_xml(archive, info)
    for node in root.iter():
        if _local_name(node.tag) != "title" or node.text is None:
            continue
        normalized = " ".join(node.text.split())[:_MAX_TITLE_CHARS]
        return normalized or None
    return None


def _extract_package_text(
    archive: ZipFile,
    entries: dict[str, ZipInfo],
    spec: _PackageSpec,
) -> str:
    if spec.mime_type == DOCX_MIME:
        values = _docx_values(archive, entries)
    elif spec.mime_type == XLSX_MIME:
        values = _xlsx_values(archive, entries)
    else:
        values = _pptx_values(archive, entries)
    return _bounded_text(values)


def _docx_values(archive: ZipFile, entries: dict[str, ZipInfo]) -> list[str]:
    root = _read_xml(archive, entries["word/document.xml"])
    return _text_nodes(root)


def _pptx_values(archive: ZipFile, entries: dict[str, ZipInfo]) -> list[str]:
    values: list[str] = []
    names = sorted(
        name
        for name in entries
        if name.startswith("ppt/slides/slide") and name.endswith(".xml")
    )
    for name in names:
        values.extend(_text_nodes(_read_xml(archive, entries[name])))
    return values


def _xlsx_values(archive: ZipFile, entries: dict[str, ZipInfo]) -> list[str]:
    shared = _shared_strings(archive, entries)
    values: list[str] = []
    sheet_names = sorted(
        name
        for name in entries
        if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
    )
    for name in sheet_names:
        root = _read_xml(archive, entries[name])
        for cell in root.iter():
            if _local_name(cell.tag) != "c":
                continue
            value = _xlsx_cell_value(cell, shared)
            if value:
                values.append(value)
    return values


def _shared_strings(archive: ZipFile, entries: dict[str, ZipInfo]) -> tuple[str, ...]:
    info = entries.get("xl/sharedStrings.xml")
    if info is None:
        return ()
    root = _read_xml(archive, info)
    strings: list[str] = []
    for item in root.iter():
        if _local_name(item.tag) != "si":
            continue
        strings.append(" ".join(_text_nodes(item)))
    return tuple(strings)


def _xlsx_cell_value(cell: ElementTree.Element, shared: tuple[str, ...]) -> str | None:
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        value = " ".join(_text_nodes(cell))
        return value or None
    raw = _first_child_text(cell, "v")
    if raw is None:
        return None
    if cell_type == "s":
        try:
            index = int(raw)
        except ValueError:
            return None
        if 0 <= index < len(shared):
            return shared[index] or None
        return None
    if cell_type == "str":
        normalized = " ".join(raw.split())
        return normalized or None
    return None


def _first_child_text(parent: ElementTree.Element, local_name: str) -> str | None:
    for node in parent:
        if _local_name(node.tag) == local_name and node.text is not None:
            return node.text
    return None


def _text_nodes(root: ElementTree.Element) -> list[str]:
    values: list[str] = []
    for node in root.iter():
        if _local_name(node.tag) != "t" or node.text is None:
            continue
        normalized = " ".join(node.text.split())
        if normalized:
            values.append(normalized)
    return values


def _read_xml(archive: ZipFile, info: ZipInfo) -> ElementTree.Element:
    if info.file_size > _MAX_ENTRY_BYTES:
        raise PublicDocumentParseError("Office Open XML XML part exceeds the parser byte limit")
    with archive.open(info, mode="r") as stream:
        data = stream.read(_MAX_ENTRY_BYTES + 1)
    if len(data) > _MAX_ENTRY_BYTES:
        raise PublicDocumentParseError("Office Open XML XML part exceeds the parser byte limit")
    lowered = data.casefold()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise PublicDocumentParseError("Office Open XML XML declarations are not permitted")
    try:
        return ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        raise PublicDocumentParseError("Office Open XML XML part is malformed") from exc


def _bounded_text(values: list[str]) -> str:
    parts: list[str] = []
    remaining = _MAX_EXTRACTED_CHARS
    for value in values:
        if remaining <= 0:
            break
        normalized = " ".join(value.split())
        if not normalized:
            continue
        bounded = normalized[:remaining]
        parts.append(bounded)
        remaining -= len(bounded)
    return " ".join(parts)[:_MAX_EXTRACTED_CHARS]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from cip.adapters.sources.public_web.parsing import PublicWebParseError

_MAX_PDF_BYTES = 5_000_000
_MAX_PDF_PAGES = 50
_MAX_EXTRACTED_CHARS = 100_000
_MAX_PLAIN_TEXT_BYTES = 1_000_000


class PublicDocumentParseError(PublicWebParseError):
    """A bounded public document could not be parsed safely."""


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    title: str | None
    language: str | None
    text: str

    @property
    def excerpt(self) -> str | None:
        return self.text[:1_000] or None


def extract_pdf_text(body: bytes) -> ExtractedDocument:
    if not body.startswith(b"%PDF-"):
        raise PublicDocumentParseError("PDF response does not contain a PDF header")
    if not body or len(body) > _MAX_PDF_BYTES:
        raise PublicDocumentParseError("PDF exceeds the parser byte limit")
    try:
        reader = PdfReader(BytesIO(body), strict=True)
    except (PdfReadError, ValueError, OSError) as exc:
        raise PublicDocumentParseError("PDF could not be parsed safely") from exc
    if reader.is_encrypted:
        raise PublicDocumentParseError("encrypted PDFs are not processed")
    page_count = len(reader.pages)
    if page_count > _MAX_PDF_PAGES:
        raise PublicDocumentParseError("PDF exceeds the parser page limit")
    parts: list[str] = []
    remaining = _MAX_EXTRACTED_CHARS
    try:
        for page in reader.pages:
            if remaining <= 0:
                break
            text = page.extract_text() or ""
            normalized = " ".join(text.split())
            if not normalized:
                continue
            bounded = normalized[:remaining]
            parts.append(bounded)
            remaining -= len(bounded)
    except (PdfReadError, ValueError, TypeError, KeyError) as exc:
        raise PublicDocumentParseError("PDF text extraction failed") from exc
    metadata = reader.metadata
    title = None
    if metadata is not None and metadata.title:
        title = " ".join(str(metadata.title).split())[:1_000] or None
    return ExtractedDocument(
        title=title,
        language=None,
        text=" ".join(parts)[:_MAX_EXTRACTED_CHARS],
    )


def extract_plain_text(body: bytes) -> ExtractedDocument:
    if not body or len(body) > _MAX_PLAIN_TEXT_BYTES:
        raise PublicDocumentParseError("text response is empty or exceeds the parser byte limit")
    try:
        decoded = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PublicDocumentParseError("text response must be valid UTF-8") from exc
    if "\x00" in decoded:
        raise PublicDocumentParseError("text response contains a NUL byte")
    normalized = " ".join(decoded.split())[:_MAX_EXTRACTED_CHARS]
    return ExtractedDocument(title=None, language=None, text=normalized)

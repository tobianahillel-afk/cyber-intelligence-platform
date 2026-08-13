from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from cip.adapters.sources.public_web.client import PublicWebFetchResult
from cip.adapters.sources.public_web.document_parsing import (
    ExtractedDocument,
    extract_pdf_text,
    extract_plain_text,
)
from cip.adapters.sources.public_web.ooxml_parsing import (
    DOCX_MIME,
    PPTX_MIME,
    XLSX_MIME,
    extract_ooxml_text,
)
from cip.adapters.sources.public_web.parsing import ExtractedHtml, extract_html
from cip.adapters.sources.public_web.semantic_html import (
    ExtractedSemanticHtml,
    extract_semantic_html,
)


@dataclass(frozen=True, slots=True)
class ExtractedPublicContent:
    title: str | None
    language: str | None
    text: str
    excerpt: str | None
    noindex: bool
    semantic_text: str = ""
    structured_text: str = ""
    published_at: datetime | None = None
    source_updated_at: datetime | None = None


def extract_public_content(
    result: PublicWebFetchResult,
    *,
    quarantined: bool,
    tombstoned: bool,
) -> ExtractedPublicContent | None:
    if quarantined or tombstoned:
        return None
    if result.mime_type == "text/html":
        return _from_html(
            extract_html(result.body),
            extract_semantic_html(result.body),
        )
    if result.mime_type == "application/pdf":
        return _from_document(extract_pdf_text(result.body))
    if result.mime_type == "text/plain":
        return _from_document(extract_plain_text(result.body))
    if result.mime_type in {DOCX_MIME, XLSX_MIME, PPTX_MIME}:
        return _from_document(
            extract_ooxml_text(result.body, mime_type=result.mime_type)
        )
    return None


def _from_html(
    extracted: ExtractedHtml,
    semantic: ExtractedSemanticHtml,
) -> ExtractedPublicContent:
    return ExtractedPublicContent(
        title=extracted.title or semantic.preferred_title,
        language=extracted.language,
        text=extracted.text,
        excerpt=extracted.excerpt,
        noindex=extracted.noindex,
        semantic_text=semantic.semantic_text,
        structured_text=semantic.structured_text,
        published_at=semantic.published_at,
        source_updated_at=semantic.source_updated_at,
    )


def _from_document(extracted: ExtractedDocument) -> ExtractedPublicContent:
    return ExtractedPublicContent(
        title=extracted.title,
        language=extracted.language,
        text=extracted.text,
        excerpt=extracted.excerpt,
        noindex=False,
    )

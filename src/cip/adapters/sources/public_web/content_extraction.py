from __future__ import annotations

from dataclasses import dataclass

from cip.adapters.sources.public_web.client import PublicWebFetchResult
from cip.adapters.sources.public_web.document_parsing import (
    ExtractedDocument,
    extract_pdf_text,
    extract_plain_text,
)
from cip.adapters.sources.public_web.parsing import ExtractedHtml, extract_html


@dataclass(frozen=True, slots=True)
class ExtractedPublicContent:
    title: str | None
    language: str | None
    text: str
    excerpt: str | None
    noindex: bool


def extract_public_content(
    result: PublicWebFetchResult,
    *,
    quarantined: bool,
    tombstoned: bool,
) -> ExtractedPublicContent | None:
    if quarantined or tombstoned:
        return None
    if result.mime_type == "text/html":
        return _from_html(extract_html(result.body))
    if result.mime_type == "application/pdf":
        return _from_document(extract_pdf_text(result.body))
    if result.mime_type == "text/plain":
        return _from_document(extract_plain_text(result.body))
    return None


def _from_html(extracted: ExtractedHtml) -> ExtractedPublicContent:
    return ExtractedPublicContent(
        title=extracted.title,
        language=extracted.language,
        text=extracted.text,
        excerpt=extracted.excerpt,
        noindex=extracted.noindex,
    )


def _from_document(extracted: ExtractedDocument) -> ExtractedPublicContent:
    return ExtractedPublicContent(
        title=extracted.title,
        language=extracted.language,
        text=extracted.text,
        excerpt=extracted.excerpt,
        noindex=False,
    )

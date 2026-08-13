from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any

_MAX_SCRIPT_CHARS = 50_000
_MAX_SCRIPTS = 8
_MAX_SCALARS = 128
_MAX_DEPTH = 12
_MAX_VALUE_CHARS = 500

_META_KEYS = frozenset(
    {
        "description",
        "keywords",
        "author",
        "application-name",
        "og:title",
        "og:description",
        "og:site_name",
        "article:published_time",
        "article:modified_time",
        "twitter:title",
        "twitter:description",
    }
)
_STRUCTURED_KEYS = frozenset(
    {
        "@type",
        "name",
        "headline",
        "description",
        "keywords",
        "category",
        "applicationcategory",
        "operatingsystem",
        "softwarerequirements",
        "jobtitle",
        "datepublished",
        "datemodified",
        "dateposted",
        "validthrough",
        "url",
        "sameas",
        "brand",
        "manufacturer",
        "provider",
        "publisher",
        "author",
        "hiringorganization",
        "about",
        "mentions",
    }
)
_SENSITIVE_KEY_MARKERS = (
    "token",
    "secret",
    "password",
    "passwd",
    "apikey",
    "api_key",
    "authorization",
    "credential",
    "session",
    "cookie",
)
_JSON_SCRIPT_TYPES = frozenset({"application/ld+json", "application/json"})


@dataclass(frozen=True, slots=True)
class ExtractedSemanticHtml:
    semantic_text: str
    structured_text: str
    preferred_title: str | None
    published_at: datetime | None
    source_updated_at: datetime | None
    structured_record_count: int


@dataclass(frozen=True, slots=True)
class _StructuredExtraction:
    values: tuple[str, ...]
    published_at: datetime | None
    source_updated_at: datetime | None


def extract_semantic_html(body: bytes) -> ExtractedSemanticHtml:
    parser = _SemanticHtmlParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    parser.close()

    semantic_values = _dedupe(parser.semantic_values)
    structured_values: list[str] = []
    published_at = _timestamp_from_meta(parser.meta_values, "article:published_time")
    source_updated_at = _timestamp_from_meta(parser.meta_values, "article:modified_time")
    record_count = 0

    for raw in parser.structured_scripts:
        extracted = _extract_json_values(raw)
        if extracted is None:
            continue
        record_count += 1
        structured_values.extend(extracted.values)
        if published_at is None:
            published_at = extracted.published_at
        if source_updated_at is None:
            source_updated_at = extracted.source_updated_at

    preferred_title = _first_non_empty(
        parser.meta_values.get("og:title"),
        parser.meta_values.get("twitter:title"),
    )
    return ExtractedSemanticHtml(
        semantic_text=" ".join(semantic_values),
        structured_text=" ".join(_dedupe(structured_values)),
        preferred_title=preferred_title,
        published_at=published_at,
        source_updated_at=source_updated_at,
        structured_record_count=record_count,
    )


class _SemanticHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.semantic_values: list[str] = []
        self.meta_values: dict[str, str] = {}
        self.structured_scripts: list[str] = []
        self._capture_script = False
        self._script_parts: list[str] = []
        self._script_chars = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        normalized = tag.casefold()
        attributes = {key.casefold(): value for key, value in attrs}
        if normalized == "meta":
            self._handle_meta(attributes)
            return
        if normalized != "script" or len(self.structured_scripts) >= _MAX_SCRIPTS:
            return
        script_type = (attributes.get("type") or "").split(";", 1)[0].strip().casefold()
        if script_type not in _JSON_SCRIPT_TYPES:
            return
        self._capture_script = True
        self._script_parts = []
        self._script_chars = 0

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() != "script" or not self._capture_script:
            return
        raw = "".join(self._script_parts).strip()
        if raw:
            self.structured_scripts.append(raw)
        self._capture_script = False
        self._script_parts = []
        self._script_chars = 0

    def handle_data(self, data: str) -> None:
        if not self._capture_script:
            return
        remaining = _MAX_SCRIPT_CHARS - self._script_chars
        if remaining <= 0:
            return
        bounded = data[:remaining]
        self._script_parts.append(bounded)
        self._script_chars += len(bounded)

    def _handle_meta(self, attributes: dict[str, str | None]) -> None:
        key = (attributes.get("property") or attributes.get("name") or "").strip().casefold()
        if key not in _META_KEYS:
            return
        content = _normalize_value(attributes.get("content"))
        if content is None:
            return
        self.meta_values.setdefault(key, content)
        self.semantic_values.append(content)


def _extract_json_values(raw: str) -> _StructuredExtraction | None:
    try:
        payload: Any = json.loads(raw)
    except (json.JSONDecodeError, RecursionError, ValueError):
        return None

    values: list[str] = []
    timestamps: dict[str, datetime] = {}
    try:
        _walk_json(payload, values=values, timestamps=timestamps, depth=0)
    except RecursionError:
        return None
    return _StructuredExtraction(
        values=tuple(_dedupe(values)),
        published_at=timestamps.get("datepublished"),
        source_updated_at=timestamps.get("datemodified"),
    )


def _walk_json(
    value: Any,
    *,
    values: list[str],
    timestamps: dict[str, datetime],
    depth: int,
    key: str | None = None,
) -> None:
    if depth > _MAX_DEPTH or len(values) >= _MAX_SCALARS:
        return
    normalized_key = key.casefold() if key is not None else None
    if normalized_key is not None and _is_sensitive_key(normalized_key):
        return
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            if not isinstance(child_key, str):
                continue
            _walk_json(
                child_value,
                values=values,
                timestamps=timestamps,
                depth=depth + 1,
                key=child_key,
            )
            if len(values) >= _MAX_SCALARS:
                return
        return
    if isinstance(value, list):
        for child in value[:_MAX_SCALARS]:
            _walk_json(
                child,
                values=values,
                timestamps=timestamps,
                depth=depth + 1,
                key=key,
            )
            if len(values) >= _MAX_SCALARS:
                return
        return
    if normalized_key not in _STRUCTURED_KEYS:
        return
    if isinstance(value, (str, int, float, bool)):
        normalized = _normalize_value(str(value))
        if normalized is None:
            return
        values.append(normalized)
        if normalized_key in {"datepublished", "datemodified"}:
            parsed = _parse_timestamp(normalized)
            if parsed is not None:
                timestamps.setdefault(normalized_key, parsed)


def _is_sensitive_key(key: str) -> bool:
    compact = key.replace("-", "").replace("_", "")
    return any(marker.replace("_", "") in compact for marker in _SENSITIVE_KEY_MARKERS)


def _timestamp_from_meta(values: dict[str, str], key: str) -> datetime | None:
    value = values.get(key)
    return _parse_timestamp(value) if value is not None else None


def _parse_timestamp(value: str) -> datetime | None:
    candidate = value.strip()
    try:
        if len(candidate) == 10:
            return datetime.fromisoformat(candidate).replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _normalize_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())[:_MAX_VALUE_CHARS]
    return normalized or None


def _dedupe(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        identity = value.casefold()
        if identity in seen:
            continue
        seen.add(identity)
        result.append(value)
    return tuple(result)


def _first_non_empty(*values: str | None) -> str | None:
    return next((value for value in values if value), None)

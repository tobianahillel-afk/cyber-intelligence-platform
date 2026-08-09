from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class OsintFrameworkCandidate:
    name: str
    url: str
    category_path: tuple[str, ...]

    @property
    def hostname(self) -> str:
        return urlparse(self.url).hostname or ""


def parse_osint_framework(payload: bytes | str) -> tuple[OsintFrameworkCandidate, ...]:
    """Normalize upstream OSINT Framework JSON without authorizing any entry."""
    decoded = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    document: object = json.loads(decoded)
    found: dict[tuple[str, str], OsintFrameworkCandidate] = {}
    _walk(document, (), found)
    return tuple(sorted(found.values(), key=lambda value: (value.name.casefold(), value.url)))


def _walk(
    node: object,
    category_path: tuple[str, ...],
    found: dict[tuple[str, str], OsintFrameworkCandidate],
) -> None:
    if isinstance(node, list):
        for child in node:
            _walk(child, category_path, found)
        return
    if not isinstance(node, dict):
        return

    name = _text(node.get("name") or node.get("title") or node.get("label"))
    url = _http_url(node.get("url") or node.get("link") or node.get("href"))
    child_path = category_path
    if name and not url:
        child_path = (*category_path, name)
    if name and url:
        key = (name.casefold(), url)
        found[key] = OsintFrameworkCandidate(name=name, url=url, category_path=category_path)

    for key, child in node.items():
        if key in {"name", "title", "label", "url", "link", "href"}:
            continue
        if isinstance(child, (dict, list)):
            _walk(child, child_path, found)


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _http_url(value: Any) -> str | None:
    text = _text(value)
    if text is None:
        return None
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    return text

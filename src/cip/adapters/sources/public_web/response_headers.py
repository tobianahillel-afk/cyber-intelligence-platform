from __future__ import annotations

from collections.abc import Iterable

_MAX_HEADER_VALUE_LENGTH = 2_000
_MAX_HEADERS = 32
_EVIDENCE_HEADER_NAMES = frozenset(
    {
        "content-language",
        "content-security-policy",
        "content-type",
        "cross-origin-embedder-policy",
        "cross-origin-opener-policy",
        "cross-origin-resource-policy",
        "permissions-policy",
        "referrer-policy",
        "server",
        "strict-transport-security",
        "via",
        "x-content-type-options",
        "x-frame-options",
        "x-powered-by",
    }
)


def bounded_evidence_headers(
    headers: Iterable[tuple[str, str]],
) -> tuple[tuple[str, str], ...]:
    selected: dict[str, str] = {}
    for raw_name, raw_value in headers:
        name = raw_name.strip().casefold()
        if name not in _EVIDENCE_HEADER_NAMES or name in selected:
            continue
        value = " ".join(raw_value.split())
        if not value:
            continue
        selected[name] = value[:_MAX_HEADER_VALUE_LENGTH]
        if len(selected) >= _MAX_HEADERS:
            break
    return tuple(sorted(selected.items()))

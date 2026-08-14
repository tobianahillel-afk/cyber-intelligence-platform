from __future__ import annotations

from collections.abc import Callable, Iterable

_MAX_HEADER_VALUE_LENGTH = 2_000
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
    return tuple(sorted(selected.items()))


def bounded_evidence_header_lookup(
    header_value: Callable[[str], str | None],
) -> tuple[tuple[str, str], ...]:
    return bounded_evidence_headers(
        (name, value)
        for name in sorted(_EVIDENCE_HEADER_NAMES)
        if (value := header_value(name)) is not None
    )

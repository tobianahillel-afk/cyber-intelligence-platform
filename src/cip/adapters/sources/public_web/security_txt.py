from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit

from cip.adapters.sources.public_web.parsing import PublicWebParseError
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl

_MAX_SECURITY_TXT_BYTES = 64_000
_MAX_FIELDS = 200
_SUPPORTED_CONTACT_SCHEMES = frozenset({"https", "mailto"})


class SecurityTxtParseError(PublicWebParseError):
    """A configured RFC 9116 security.txt file failed bounded validation."""


@dataclass(frozen=True, slots=True)
class SecurityTxtDocument:
    contacts: tuple[str, ...]
    canonical_urls: tuple[str, ...]
    expires_at: datetime | None
    preferred_languages: tuple[str, ...]


def parse_security_txt(body: bytes, target: PublicWebTarget) -> SecurityTxtDocument:
    if not body or len(body) > _MAX_SECURITY_TXT_BYTES:
        raise SecurityTxtParseError("security.txt is empty or exceeds the parser byte limit")
    try:
        text = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise SecurityTxtParseError("security.txt must be valid UTF-8") from exc
    if "\x00" in text:
        raise SecurityTxtParseError("security.txt contains a NUL byte")
    fields = _fields(text)
    contacts = tuple(
        value
        for name, value in fields
        if name == "contact" and _valid_contact(value)
    )
    if not contacts:
        raise SecurityTxtParseError("security.txt requires at least one valid Contact field")
    canonical_urls = _canonical_urls(fields, target)
    expires_at = _expires_at(fields)
    languages = _preferred_languages(fields)
    return SecurityTxtDocument(
        contacts=contacts,
        canonical_urls=canonical_urls,
        expires_at=expires_at,
        preferred_languages=languages,
    )


def bounded_security_txt_excerpt(
    document: SecurityTxtDocument,
    *,
    maximum: int = 1_000,
) -> str:
    if not 1 <= maximum <= 4_000:
        raise ValueError("security.txt excerpt bound must be between 1 and 4000")
    parts = [*(f"Contact: {value}" for value in document.contacts)]
    parts.extend(f"Canonical: {value}" for value in document.canonical_urls)
    if document.expires_at is not None:
        parts.append(f"Expires: {document.expires_at.isoformat()}")
    if document.preferred_languages:
        parts.append(f"Preferred-Languages: {', '.join(document.preferred_languages)}")
    return "\n".join(parts)[:maximum]


def _fields(text: str) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if len(result) >= _MAX_FIELDS:
            raise SecurityTxtParseError("security.txt contains too many fields")
        name, separator, raw_value = stripped.partition(":")
        if not separator:
            continue
        normalized_name = name.strip().casefold()
        value = raw_value.strip()
        if normalized_name and value:
            result.append((normalized_name, value[:4_000]))
    return tuple(result)


def _valid_contact(value: str) -> bool:
    parsed = urlsplit(value)
    if parsed.scheme.casefold() not in _SUPPORTED_CONTACT_SCHEMES:
        return False
    if parsed.scheme.casefold() == "mailto":
        address = parsed.path.strip()
        return "@" in address and not any(char.isspace() for char in address)
    try:
        CanonicalUrl(value)
    except ValueError:
        return False
    return True


def _canonical_urls(
    fields: tuple[tuple[str, str], ...],
    target: PublicWebTarget,
) -> tuple[str, ...]:
    expected = CanonicalUrl(target.security_txt_url).value
    values: list[str] = []
    for name, value in fields:
        if name != "canonical":
            continue
        try:
            canonical = CanonicalUrl(value).value
        except ValueError as exc:
            raise SecurityTxtParseError("security.txt Canonical field is invalid") from exc
        if canonical != expected:
            raise SecurityTxtParseError(
                "security.txt Canonical field does not match the configured exact path"
            )
        if canonical not in values:
            values.append(canonical)
    return tuple(values)


def _expires_at(fields: tuple[tuple[str, str], ...]) -> datetime | None:
    value = next((value for name, value in fields if name == "expires"), None)
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SecurityTxtParseError("security.txt Expires field is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SecurityTxtParseError("security.txt Expires field requires a timezone")
    return parsed.astimezone(UTC)


def _preferred_languages(
    fields: tuple[tuple[str, str], ...],
) -> tuple[str, ...]:
    raw = next((value for name, value in fields if name == "preferred-languages"), None)
    if raw is None:
        return ()
    languages = tuple(
        token.strip().casefold()
        for token in raw.split(",")
        if token.strip()
    )
    return languages[:20]

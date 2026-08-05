from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_ALLOWED_SCHEMES = {"http", "https"}
_DEFAULT_PORTS = {"http": 80, "https": 443}


@dataclass(frozen=True, slots=True)
class CanonicalUrl:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", canonicalize_url(self.value))

    @property
    def host(self) -> str:
        return urlsplit(self.value).hostname or ""

    @property
    def path(self) -> str:
        return urlsplit(self.value).path or "/"

    @property
    def origin(self) -> str:
        parsed = urlsplit(self.value)
        return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def canonicalize_url(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError("URL is required")
    parsed = urlsplit(candidate)
    scheme = parsed.scheme.casefold()
    if scheme not in _ALLOWED_SCHEMES:
        raise ValueError("URL scheme must be http or https")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL cannot contain embedded credentials")
    if parsed.hostname is None:
        raise ValueError("URL host is required")

    host = parsed.hostname.encode("idna").decode("ascii").casefold()
    port = parsed.port
    netloc = host
    if port is not None and port != _DEFAULT_PORTS[scheme]:
        netloc = f"{host}:{port}"

    path = parsed.path or "/"
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    query = urlencode(sorted(query_pairs), doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def same_origin(first: str | CanonicalUrl, second: str | CanonicalUrl) -> bool:
    first_url = first if isinstance(first, CanonicalUrl) else CanonicalUrl(first)
    second_url = second if isinstance(second, CanonicalUrl) else CanonicalUrl(second)
    return first_url.origin == second_url.origin

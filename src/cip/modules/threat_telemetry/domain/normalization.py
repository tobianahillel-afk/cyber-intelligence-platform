from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_HASH_LENGTHS = {
    32: "md5",
    40: "sha1",
    64: "sha256",
}
_DEFAULT_PORTS = {"http": 80, "https": 443}


def normalize_ip(value: str, *, version: int) -> str:
    try:
        address = ip_address(value.strip())
    except ValueError as exc:
        raise ValueError("indicator must be a valid IP address") from exc
    if address.version != version:
        raise ValueError(f"indicator must be IPv{version}")
    return address.compressed.casefold()


def normalize_domain(value: str) -> str:
    candidate = value.strip().rstrip(".")
    if not candidate:
        raise ValueError("domain indicator is required")
    try:
        ip_address(candidate)
    except ValueError:
        pass
    else:
        raise ValueError("domain indicator cannot be an IP address")
    try:
        normalized = candidate.encode("idna").decode("ascii").casefold()
    except UnicodeError as exc:
        raise ValueError("domain indicator is not valid IDNA") from exc
    labels = normalized.split(".")
    if len(normalized) > 253 or any(
        not label or len(label) > 63 or label.startswith("-") or label.endswith("-")
        for label in labels
    ):
        raise ValueError("domain indicator is malformed")
    return normalized


def normalize_url(value: str) -> str:
    candidate = value.strip()
    parsed = urlsplit(candidate)
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"}:
        raise ValueError("URL indicator must use http or https")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL indicator cannot contain embedded credentials")
    if parsed.hostname is None:
        raise ValueError("URL indicator host is required")
    host = _normalize_url_host(parsed.hostname)
    rendered_host = f"[{host}]" if ":" in host else host
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("URL indicator port is invalid") from exc
    netloc = rendered_host
    if port is not None and port != _DEFAULT_PORTS[scheme]:
        netloc = f"{rendered_host}:{port}"
    path = parsed.path or "/"
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)), doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_hash(value: str, *, certificate: bool = False) -> str:
    candidate = value.strip().casefold().replace(":", "")
    if any(character not in "0123456789abcdef" for character in candidate):
        raise ValueError("hash indicator must be hexadecimal")
    algorithm = _HASH_LENGTHS.get(len(candidate))
    if algorithm is None:
        raise ValueError("hash indicator must be MD5, SHA-1, or SHA-256")
    prefix = "certificate" if certificate else "file"
    return f"{prefix}:{algorithm}:{candidate}"


def normalize_email(value: str) -> str:
    candidate = value.strip()
    if candidate.count("@") != 1:
        raise ValueError("email indicator must contain one @")
    local, domain = candidate.rsplit("@", 1)
    if not local or len(local) > 64:
        raise ValueError("email indicator local part is invalid")
    return f"{local.casefold()}@{normalize_domain(domain)}"


def _normalize_url_host(value: str) -> str:
    try:
        return ip_address(value).compressed.casefold()
    except ValueError:
        return normalize_domain(value)

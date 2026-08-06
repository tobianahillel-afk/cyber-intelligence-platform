from __future__ import annotations

import re
from ipaddress import IPv4Address, IPv6Address, ip_address

_LOCAL_SUFFIXES = (
    ".internal",
    ".intranet",
    ".lan",
    ".local",
    ".localhost",
    ".test",
)
_ASN_PATTERN = re.compile(r"^(?:AS)?(?P<number>[0-9]{1,10})$", re.IGNORECASE)
_PROTOCOL_PATTERN = re.compile(r"^[a-z][a-z0-9+._-]{0,31}$")
_HEX_PATTERN = re.compile(r"^[0-9a-f]+$")
_CLOUD_NAMESPACE_PATTERN = re.compile(r"^[a-z][a-z0-9._-]{0,99}$")


def normalize_domain(value: str) -> str:
    candidate = value.strip().rstrip(".")
    if not candidate or len(candidate) > 253:
        raise ValueError("domain must be between 1 and 253 characters")
    try:
        normalized = candidate.encode("idna").decode("ascii").casefold()
    except UnicodeError as exc:
        raise ValueError("domain must be valid IDNA") from exc
    if normalized == "localhost" or normalized.endswith(_LOCAL_SUFFIXES):
        raise ValueError("local or internal domains are not accepted")
    labels = normalized.split(".")
    if len(labels) < 2:
        raise ValueError("domain must have a registrable suffix")
    if any(not _valid_label(label) for label in labels):
        raise ValueError("domain contains an invalid label")
    return normalized


def normalize_hostname(value: str) -> str:
    return normalize_domain(value)


def normalize_ip(value: str, *, version: int | None = None) -> str:
    try:
        address = ip_address(value.strip())
    except ValueError as exc:
        raise ValueError("IP address is invalid") from exc
    if version == 4 and not isinstance(address, IPv4Address):
        raise ValueError("expected an IPv4 address")
    if version == 6 and not isinstance(address, IPv6Address):
        raise ValueError("expected an IPv6 address")
    if not address.is_global:
        raise ValueError("only globally routable IP addresses are accepted")
    return address.compressed


def normalize_asn(value: str) -> str:
    match = _ASN_PATTERN.fullmatch(value.strip())
    if match is None:
        raise ValueError("ASN must use AS123 or 123 format")
    number = int(match.group("number"))
    if not 1 <= number <= 4_294_967_295:
        raise ValueError("ASN is outside the supported range")
    return f"AS{number}"


def normalize_certificate_fingerprint(value: str) -> str:
    normalized = value.strip().casefold().replace(":", "").replace("-", "")
    if len(normalized) not in {40, 64, 128} or _HEX_PATTERN.fullmatch(normalized) is None:
        raise ValueError("certificate fingerprint must be SHA-1, SHA-256, or SHA-512 hex")
    return normalized


def normalize_cloud_resource(value: str) -> str:
    candidate = value.strip()
    if not candidate or len(candidate) > 500:
        raise ValueError("cloud resource identifier must be bounded")
    if any(character.isspace() for character in candidate):
        raise ValueError("cloud resource identifier cannot contain whitespace")
    namespace, separator, resource = candidate.partition(":")
    normalized_namespace = namespace.casefold()
    if (
        not separator
        or not resource
        or _CLOUD_NAMESPACE_PATTERN.fullmatch(normalized_namespace) is None
    ):
        raise ValueError(
            "cloud resource identifier must include a valid provider namespace"
        )
    return f"{normalized_namespace}:{resource}"


def normalize_protocol(value: str) -> str:
    normalized = value.strip().casefold()
    if _PROTOCOL_PATTERN.fullmatch(normalized) is None:
        raise ValueError("protocol must be a bounded machine-readable value")
    return normalized


def normalize_port(value: int) -> int:
    if not 1 <= value <= 65_535:
        raise ValueError("port must be between 1 and 65535")
    return value


def normalize_optional_text(value: str | None, *, maximum: int) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > maximum:
        raise ValueError(f"text value cannot exceed {maximum} characters")
    return normalized


def _valid_label(label: str) -> bool:
    return (
        1 <= len(label) <= 63
        and not label.startswith("-")
        and not label.endswith("-")
        and all(character.isalnum() or character == "-" for character in label)
    )

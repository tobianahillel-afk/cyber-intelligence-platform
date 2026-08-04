from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from cip.shared.kernel.time import require_aware_utc

_NON_ALNUM = re.compile(r"[^A-Z0-9]")
_FOREIGN_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._/-]{1,63}$")


class IdentifierScheme(StrEnum):
    SIREN = "siren"
    SIRET = "siret"
    LEI = "lei"
    FOREIGN_REGISTRATION = "foreign_registration"


@dataclass(frozen=True, slots=True)
class OfficialIdentifier:
    scheme: IdentifierScheme
    value: str
    source_id: str
    verified_at: datetime
    issuing_country: str | None = None
    is_current: bool = True

    def __post_init__(self) -> None:
        source_id = self.source_id.strip()
        if not source_id:
            raise ValueError("source_id is required")
        object.__setattr__(self, "source_id", source_id)
        country = _normalize_country(self.issuing_country)
        normalized = normalize_identifier(self.scheme, self.value, country)
        object.__setattr__(self, "value", normalized)
        object.__setattr__(self, "issuing_country", country)
        object.__setattr__(
            self,
            "verified_at",
            require_aware_utc(self.verified_at, field_name="verified_at"),
        )

    @property
    def exact_key(self) -> str:
        country = self.issuing_country or ""
        return f"{self.scheme.value}:{country}:{self.value}"


def normalize_identifier(
    scheme: IdentifierScheme,
    value: str,
    issuing_country: str | None = None,
) -> str:
    normalized = _NON_ALNUM.sub("", value.strip().upper())
    if scheme is IdentifierScheme.SIREN:
        _validate_siren(normalized)
    elif scheme is IdentifierScheme.SIRET:
        _validate_siret(normalized)
    elif scheme is IdentifierScheme.LEI:
        _validate_lei(normalized)
    else:
        if issuing_country is None:
            raise ValueError("foreign registration identifiers require issuing_country")
        if not _FOREIGN_PATTERN.fullmatch(value.strip().upper()):
            raise ValueError("foreign registration identifier has an invalid format")
        normalized = value.strip().upper()
    return normalized


def identifier_from_registration_id(
    value: str,
    *,
    source_id: str,
    verified_at: datetime,
) -> OfficialIdentifier | None:
    raw = value.strip()
    if not raw:
        return None
    prefix, separator, identifier = raw.partition(":")
    if separator:
        try:
            scheme = IdentifierScheme(prefix.casefold())
        except ValueError:
            return None
        country = (
            "FR"
            if scheme in {IdentifierScheme.SIREN, IdentifierScheme.SIRET}
            else None
        )
        return OfficialIdentifier(
            scheme=scheme,
            value=identifier,
            source_id=source_id,
            verified_at=verified_at,
            issuing_country=country,
        )
    digits = _NON_ALNUM.sub("", raw.upper())
    if len(digits) == 9 and digits.isdigit():
        scheme = IdentifierScheme.SIREN
    elif len(digits) == 14 and digits.isdigit():
        scheme = IdentifierScheme.SIRET
    elif len(digits) == 20:
        scheme = IdentifierScheme.LEI
    else:
        return None
    country = (
        "FR" if scheme in {IdentifierScheme.SIREN, IdentifierScheme.SIRET} else None
    )
    return OfficialIdentifier(
        scheme=scheme,
        value=digits,
        source_id=source_id,
        verified_at=verified_at,
        issuing_country=country,
    )


def _validate_siren(value: str) -> None:
    if len(value) != 9 or not value.isdigit():
        raise ValueError("SIREN must contain exactly 9 digits")
    if not _passes_luhn(value):
        raise ValueError("SIREN checksum is invalid")


def _validate_siret(value: str) -> None:
    if len(value) != 14 or not value.isdigit():
        raise ValueError("SIRET must contain exactly 14 digits")
    if not _passes_luhn(value):
        raise ValueError("SIRET checksum is invalid")


def _validate_lei(value: str) -> None:
    if len(value) != 20 or not value.isalnum():
        raise ValueError("LEI must contain exactly 20 alphanumeric characters")
    expanded = "".join(
        str(ord(character) - 55) if character.isalpha() else character
        for character in value
    )
    if _mod97(expanded) != 1:
        raise ValueError("LEI checksum is invalid")


def _passes_luhn(value: str) -> bool:
    total = 0
    parity = len(value) % 2
    for index, character in enumerate(value):
        digit = int(character)
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _mod97(value: str) -> int:
    remainder = 0
    for character in value:
        remainder = (remainder * 10 + int(character)) % 97
    return remainder


def _normalize_country(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    if len(normalized) != 2 or not normalized.isalpha():
        raise ValueError("issuing_country must be an ISO alpha-2 code")
    return normalized

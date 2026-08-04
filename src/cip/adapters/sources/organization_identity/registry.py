from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml

from cip.modules.organizations.domain.identifiers import (
    IdentifierScheme,
    OfficialIdentifier,
)

_REGISTRY_TIME = datetime(2000, 1, 1, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class OrganizationIdentityTarget:
    id: str
    organization_id: UUID
    canonical_name: str
    country_code: str
    query: str
    postal_code: str | None = None
    siren: str | None = None
    siret: str | None = None
    lei: str | None = None
    enabled: bool = True

    def __post_init__(self) -> None:
        for field_name in ("id", "canonical_name", "query"):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} is required")
            object.__setattr__(self, field_name, value)
        country = self.country_code.strip().upper()
        if len(country) != 2 or not country.isalpha():
            raise ValueError("country_code must be an ISO alpha-2 code")
        object.__setattr__(self, "country_code", country)
        if self.postal_code is not None:
            postal_code = self.postal_code.strip()
            object.__setattr__(self, "postal_code", postal_code or None)
        for field_name, scheme in (
            ("siren", IdentifierScheme.SIREN),
            ("siret", IdentifierScheme.SIRET),
            ("lei", IdentifierScheme.LEI),
        ):
            value = getattr(self, field_name)
            if value is None:
                continue
            identifier = OfficialIdentifier(
                scheme=scheme,
                value=value,
                source_id="target-registry",
                verified_at=_REGISTRY_TIME,
                issuing_country="FR" if scheme is not IdentifierScheme.LEI else None,
            )
            object.__setattr__(self, field_name, identifier.value)

    def known_identifiers(
        self,
        *,
        source_id: str,
        verified_at: datetime,
    ) -> tuple[OfficialIdentifier, ...]:
        identifiers: list[OfficialIdentifier] = []
        for value, scheme in (
            (self.siren, IdentifierScheme.SIREN),
            (self.siret, IdentifierScheme.SIRET),
            (self.lei, IdentifierScheme.LEI),
        ):
            if value is None:
                continue
            identifiers.append(
                OfficialIdentifier(
                    scheme=scheme,
                    value=value,
                    source_id=source_id,
                    verified_at=verified_at,
                    issuing_country="FR" if scheme is not IdentifierScheme.LEI else None,
                )
            )
        return tuple(identifiers)


def load_organization_identity_targets(
    path: Path,
) -> tuple[OrganizationIdentityTarget, ...]:
    payload = _load_yaml_mapping(path)
    if _positive_int(payload, "version") != 1:
        raise ValueError("unsupported organization identity target registry version")
    raw_targets = payload.get("targets")
    if not isinstance(raw_targets, list):
        raise ValueError("targets must be a list")
    targets: list[OrganizationIdentityTarget] = []
    ids: set[str] = set()
    organization_ids: set[UUID] = set()
    for raw in raw_targets:
        if not isinstance(raw, dict):
            raise ValueError("each organization identity target must be a mapping")
        target = _parse_target(raw)
        if target.id in ids:
            raise ValueError(f"duplicate organization identity target id: {target.id}")
        if target.organization_id in organization_ids:
            raise ValueError(
                f"duplicate organization identity target organization_id: {target.organization_id}"
            )
        ids.add(target.id)
        organization_ids.add(target.organization_id)
        targets.append(target)
    return tuple(targets)


def _parse_target(payload: dict[str, Any]) -> OrganizationIdentityTarget:
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean")
    organization_id = _required_string(payload, "organization_id")
    try:
        parsed_organization_id = UUID(organization_id)
    except ValueError as exc:
        raise ValueError("organization_id must be a UUID") from exc
    return OrganizationIdentityTarget(
        id=_required_string(payload, "id"),
        organization_id=parsed_organization_id,
        canonical_name=_required_string(payload, "canonical_name"),
        country_code=_required_string(payload, "country_code"),
        query=_required_string(payload, "query"),
        postal_code=_optional_string(payload, "postal_code"),
        siren=_optional_string(payload, "siren"),
        siret=_optional_string(payload, "siret"),
        lei=_optional_string(payload, "lei"),
        enabled=enabled,
    )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("organization identity registry root must be a mapping")
    return loaded


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string or null")
    return value


def _positive_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{key} must be a positive integer")
    return value

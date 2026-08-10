from __future__ import annotations

from enum import StrEnum
from ipaddress import IPv4Address, IPv6Address, ip_address
from pathlib import Path
from uuid import UUID

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from cip.modules.passive_exposure.domain.normalization import normalize_domain


class RdapTargetKind(StrEnum):
    DOMAIN = "domain"
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    ASN = "asn"


class RdapTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    target_id: str = Field(min_length=1, max_length=200)
    organization_id: UUID
    kind: RdapTargetKind
    value: str = Field(min_length=1, max_length=253)
    enabled: bool = False

    @model_validator(mode="after")
    def normalize_value(self) -> RdapTarget:
        if self.kind is RdapTargetKind.DOMAIN:
            self.value = _domain(self.value)
        elif self.kind is RdapTargetKind.IPV4:
            self.value = str(_ip(self.value, IPv4Address))
        elif self.kind is RdapTargetKind.IPV6:
            self.value = str(_ip(self.value, IPv6Address))
        else:
            self.value = _asn(self.value)
        return self


class RdapTargetFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1, le=1)
    targets: list[RdapTarget] = Field(default_factory=list, max_length=500)


def load_rdap_targets(path: Path) -> tuple[RdapTarget, ...]:
    parsed = RdapTargetFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    targets = tuple(parsed.targets)
    target_ids = [target.target_id for target in targets]
    identities = [(target.kind, target.value) for target in targets]
    if len(target_ids) != len(set(target_ids)):
        raise ValueError("duplicate RDAP target_id")
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate RDAP target resource")
    return targets


def _domain(value: str) -> str:
    candidate = value.rstrip(".")
    try:
        ip_address(candidate)
    except ValueError:
        return normalize_domain(candidate)
    raise ValueError("RDAP domain target cannot be an IP literal")


def _ip(value: str, expected: type[IPv4Address] | type[IPv6Address]):
    parsed = ip_address(value)
    if not isinstance(parsed, expected):
        raise ValueError(f"RDAP target must be {expected.__name__}")
    if not parsed.is_global:
        raise ValueError("RDAP IP target must be globally routable")
    return parsed


def _asn(value: str) -> str:
    candidate = value.upper().removeprefix("AS")
    if not candidate.isdigit():
        raise ValueError("RDAP ASN target must be an AS number")
    number = int(candidate)
    if not 1 <= number <= 4_294_967_295:
        raise ValueError("RDAP ASN target is outside the 32-bit AS number range")
    return f"AS{number}"
